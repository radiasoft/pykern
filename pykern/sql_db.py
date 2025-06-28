"""EXPERIMENTAL sqlalchemy wrapper

This interface is GOING TO CHANGE.

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import datetime
import pykern.pkconfig
import pykern.pkinspect
import pykern.pkio
import pykern.util
import re
import sqlalchemy
import sqlalchemy.sql.operators
import sys

_NULLABLE_DECL = "nullable"

_PRIMARY_ID_DECL = "primary_id"

# Used in "is" comparisons so all primary_ids share the same type
_PRIMARY_ID_STYPE = sqlalchemy.types.BigInteger()

_TABLE_MODIFIERS = frozenset(("foreign", "index", "unique"))

_COL_MODIFIERS = frozenset(
    ("foreign", "index", _NULLABLE_DECL, "primary_key", "unique")
)

_STYPE_MAP = PKDict(
    {
        "bool": sqlalchemy.types.Boolean(),
        "datetime": sqlalchemy.types.DateTime(),
        "float 32": sqlalchemy.types.Float(precision=24),
        "float 64": sqlalchemy.types.Float(precision=53),
        "int 32": sqlalchemy.types.Integer(),
        "int 64": sqlalchemy.types.BigInteger(),
        _PRIMARY_ID_DECL: _PRIMARY_ID_STYPE,
        # str is a special case
        "text": sqlalchemy.types.Text(),
    }
)

_PRIMARY_ID_INC = 1000

_PRIMARY_ID_MOD = _PRIMARY_ID_INC // 10

_QUALIFIER = re.compile(r"^\d+$")

_STR_DECL = "str"

# Denormalization is ok since _STYPE_MAP is checked.
_TYPE_NAMES = frozenset(
    {"bool", "datetime", "float", "int", _PRIMARY_ID_DECL, _STR_DECL, "text"}
)

_cfg = pykern.pkconfig.init(
    debug=(False, bool, "turn on sqlalchemy tracing"),
)


class BaseExc(Exception):
    """Superclass for sll exceptions in this module"""

    def __init__(self, **context):
        a = [self.__class__.__name__]
        f = "exception={}"
        for k, v in context.items():
            f += " {}={}"
            a.extend([k, v])
        pkdlog(f, *a)

    def as_api_error(self):
        return pykern.util.APIError("db_error={}", self.__class__.__name__)


class NoRows(BaseExc):
    """Expected at least one row, but got none."""

    pass


class MoreThanOneRow(BaseExc):
    """Expected exactly one row, but got more than one."""

    pass


class Meta:
    """A practical wrapper for sqlalchemy.engine and session objects.

    Schema specification is designed to reduce boilerplate.  The general form is:
    ``{table(s): {columns(s): "type modifier(s)", constraint(s): val}``.

    A detailed schema example is in ``tests/sql_db_test.py``.

    The type must be one of: bool, datetime, float, int, primary_id,
    str, text. float and int are followed by a size of 32 or 64.  str
    is followed by a size of any length.

    Column modifiers are separated by spaces.

    foreign
        The column name matches the first primary_key of another table

    index
        An index will be created

    nullable
        When passed, sqlalchemy will get nullable=False

    primary_id
        Two modes: with and without an int qualifier. With a qualifier,
        makes the column a primary_key using the int qualifier as a base for
        the sequence. The int must be between 0 and 100 (exclusive). The sequence
        is a series: `10<nn>`, `20<nn>`, ... The advantage to this is that all
        primary_ids are globally unique and can be "type checked" by higher level
        code.

        When used without a qualifier, refers to the primary_id of
        another table by exactly the same name. A ForeignKeyConstraint
        and Index will be added to that other table.

    primary_key
        Passes primary_key=True

    unique
        Column must have unique values (index will be created)

    Table constraints:

    foreign
        Iterable of arguments to `sqlalchemy.ForeignKeyConstraint`.
        Also, creates an index.

    index
        Iterable of arguments to `sqlalchemy.Index` except for the index name which
        is always created.

    unique
        Iterable of arguments to `sqlalchemy.UniqueConstraint`.
    Args:
        uri (str): sqlite:///<file> or postgresql://<user>:<pass>@localhost:5432/<db>
        schema (PKDict): see description above.

    """

    def __init__(self, uri, schema):
        # TODO(robnagler): need to set connection args, e.g. pooling
        self.uri = uri
        self._is_sqlite = uri.startswith("sqlite")
        self._engine = sqlalchemy.create_engine(uri, echo=_cfg.debug)
        self._table_wraps = _TableBuilder(self, schema).table_wraps
        self._all_tables = PKDict(
            {
                k: self.table(k)
                for k in sqlalchemy.inspect(self._engine).get_table_names()
            }
        )
        self.tables = self.t = self.tables(as_dict=True)

    def session(self):
        # is context manager so can be with or not
        # TODO(robnagler) keep track of sessions?
        return _Session(self)

    def table(self, name):
        return self._table_wrap(name).table

    def tables(self, *names, as_dict=False):
        if len(names) == 0:
            if not as_dict:
                raise AssertionError("as_dict must be true if there are no names")
            return self._all_tables.copy()
        rv = (self.t[n] for n in names)
        if as_dict:
            return PKDict(zip(names, rv))
        return rv

    def _table_wrap(self, table_or_name):
        if isinstance(table_or_name, str):
            return self._table_wraps[table_or_name.lower()]
        if n := getattr(table_or_name, "name", None):
            return self._table_wraps[n]
        raise AssertionError(
            f"must be a sqlalchemy.Table or string type={table_or_name}"
        )


def sqlite_uri(path):
    """Converts absolute path to sqlalchemy uri for sqlite

    Args:
        path (str or py.path): path which will be made absolute
    Returns:
        str: sqlalchemy compatible (see ``Meta``) uri
    """
    return "sqlite:///" + str(pykern.pkio.py_path(path))


class _Session:
    """Holds SQLAlchemy connection.

    All quests automatically begin a transaction at start and commit
    on success or rollback on an exception.
    """

    def __init__(self, meta, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = None
        self._txn = None
        self.meta = meta
        self.tables = self.t = self.meta.tables

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args, **kwargs):
        self.commit_or_rollback(commit=exc_type is None)

    def column_map(self, table, key_col, value_col, where):
        return PKDict({r[key_col]: r[value_col] for r in self.select(table, where)})

    def commit(self):
        self.commit_or_rollback(commit=True)

    def commit_or_rollback(self, commit):
        if self._conn is None:
            return
        c = self._conn
        t = self._txn
        try:
            self._conn = None
            self._txn = None
            if commit:
                t.commit()
            else:
                t.rollback()
        finally:
            c.close()

    def destroy(self, commit=False, **kwargs):
        self.commit_or_rollback(commit=commit)

    def execute(self, stmt):
        return self.__conn().execute(stmt)

    def insert(self, table, *args, **kwargs):
        """Insert a record into the db.

        Args:
            table (str): name of the table to insert into
            values (dict, list, tuple): passed to PKDict
            kwargs (dict): columns in a `PKDict` (``args`` must be empty)
        Returns:
            PKDict: inserted values with primary_id (if generated)
        """
        w = self.meta._table_wrap(table)
        v = w.fixup_pre_insert(self, self.__varargs(args, kwargs))
        return w.fixup_post_insert(
            self,
            v,
            # defined by sqlalchemy
            getattr(
                self.execute(w.table.insert().values(v)),
                "inserted_primary_key",
                None,
            ),
        )

    def rollback(self):
        self.commit_or_rollback(commit=False)

    def select(self, table_or_stmt, where=None):
        def _stmt(table):
            rv = sqlalchemy.select(table)
            if not where:
                return rv
            return rv.where(
                *(
                    sqlalchemy.sql.operators.eq(table.columns[k], v)
                    for k, v in where.items()
                )
            )

        return self.execute(
            _stmt(self.t[table_or_stmt])
            if isinstance(table_or_stmt, str)
            else table_or_stmt
        )

    def select_max_primary_id(self, table):
        w = self.meta._table_wrap(table)
        return self.execute(
            sqlalchemy.select(
                sqlalchemy.func.max(w.table.columns[w.primary_id]),
            )
        ).scalar()

    def select_or_insert(self, table, *args, **kwargs):
        v = self.__varargs(args, kwargs)
        if m := self.select_one_or_none(table, where=v):
            return m
        return self.insert(table, v)

    def select_one(self, table_or_stmt, where=None):
        if rv := self.select_one_or_none(table_or_stmt, where):
            return rv
        raise NoRows(table_or_stmt=table_or_stmt, where=where)

    def select_one_or_none(self, table_or_stmt, where):
        rv = None
        for x in self.select(table_or_stmt, where):
            if rv is not None:
                raise MoreThanOneRow(table_or_stmt=table_or_stmt, where=where)
            rv = x
        return rv

    def __conn(self):
        if self._conn is None:
            self._conn = self.meta._engine.connect()
            self._txn = self._conn.begin()
        return self._conn

    def __varargs(self, args, kwargs):
        if len(args) == 1:
            if kwargs:
                raise AssertionError(
                    f"may only have one args={args} or kwargs={kwargs}"
                )
            return PKDict(args[0])
        if len(args) > 1:
            raise AssertionError(f"too many args={args}, must be one or zero)")
        return PKDict(kwargs)


class _TableWrap:
    """Wraps an `sqlalchemy.Table`

    See `sqlalchemy.db` for how to get instances of this class.

    Public attributes:

    has_created
        whether the table as a `sqlalchemy.types.DateTime` column named `created`.
    has_primary_id
        whether table has a `sqlalchemy.types.BigInteger` column that is the primary
        key which is generated by a sequence (only needed for `sqlite`)
    name
        the "class" name style for the table, but not a class, e.g. ``RunKind``.
    primary_id_start
        first value for primary id (only needed for `sqlite`)
    table
        sqlalchemy.Table describing the table

    """

    def __init__(self, table):
        self.table = table
        self.has_created = "created" in table.columns
        # primary_id only needed for sqlite (see _Session.insert)
        c = list(table.primary_key)[0]
        self.has_primary_id = isinstance(c.default, sqlalchemy.Sequence)
        if self.has_primary_id:
            self.primary_id = c.name
            self.primary_id_start = c.default.start

    def fixup_post_insert(self, db, values, inserted_primary_key):
        """Add in inserted_primary_key if is not None.

        Args:
            db (db._Db): database object
            values (PKDict): values to insert
        Returns:
            PKDict: modified values
        """
        # we do not handle multi column inserted_primary_keys
        if self.has_primary_id and inserted_primary_key is not None:
            values[self.primary_id] = inserted_primary_key[self.primary_id]
        return values

    def fixup_pre_insert(self, session, values):
        """Called before sqlalchemy insert to add missing columns

        Adds ``created`` field if table has a created column and
        values does not have a ``created`` key.

        For sqlite, adds ``primary_id`` if table has a primary id and
        values does not have one.

        Args:
            db (db._Db): database object
            values (PKDict): values to insert
        Returns:
            PKDict: modified values

        """
        if self.has_created and "created" not in values:
            values.created = datetime.datetime.utcnow()
        if (
            session.meta._is_sqlite
            and self.has_primary_id
            and self.primary_id not in values
        ):
            v = session.select_max_primary_id(self.table.name)
            values[self.primary_id] = (
                self.primary_id_start if v is None else v + _PRIMARY_ID_INC
            )
        return values


class _TableBuilder:
    """Defines the schema for SQLAlchemy"""

    def __init__(self, meta, schema):
        self._meta = meta
        self._metadata = sqlalchemy.MetaData()
        self.table_wraps = PKDict()
        self._primary_id_cols = set()
        self._primary_key_cols = PKDict()
        for s in self._parser(schema):
            self.table_wraps[s.name] = self._table_create(s)
        self._metadata.create_all(bind=meta._engine)

    def _parser(self, schema):

        def _col_decl(name, decl):
            rv = PKDict(name=name)
            for d in decl.lower().split(" "):
                if d in _COL_MODIFIERS:
                    rv[d] = True
                elif _QUALIFIER.search(d):
                    if "stype_qualifier" in rv:
                        raise AssertionError(f"duplicate qualifier={d}")
                    rv.stype_qualifier = int(d)
                elif d in _TYPE_NAMES:
                    rv.stype_name = d
                else:
                    raise AssertionError(f"invalid declaration={d}")
            rv.stype = _stype(decl, rv)
            return rv

        def _ident(name, which, name_set):
            rv = name.lower()
            if rv in _RESERVED_IN_SQLITE_POSTGRES:
                raise AssertionError(f"{which}={rv} is a reserved word")
            if rv in name_set:
                raise AssertionError(f"{which}={rv} is a duplicate (case insensitive)")
            name_set.add(rv)
            return rv

        def _stype(decl, spec):
            if (t := spec.pkdel("stype_name")) is None:
                raise AssertionError(f"missing type name")
            if (q := spec.pkdel("stype_qualifier")) is not None:
                if t == _STR_DECL:
                    return sqlalchemy.types.String(q)
                if t == _PRIMARY_ID_DECL:
                    if not (0 < q < _PRIMARY_ID_MOD):
                        raise AssertionError(
                            f"{_PRIMARY_ID_DECL} qualifier must be between 0 and {_PRIMARY_ID_MOD}",
                        )
                    # SIDE-EFFECT: nested function so limited scope
                    spec.sequence = q
                    return _PRIMARY_ID_STYPE
                if t in _STYPE_MAP:
                    raise AssertionError(f"type={t} does not accept a qualifier={q}")
                t += f" {q}"
            # POSIT: _table_create does more checking of primary_id
            if (rv := _STYPE_MAP.get(t)) is None:
                raise AssertionError(f"type={t} not found or incorrect qualifier")
            return rv

        def _table_decl(table_name, decl, table_set):
            rv = PKDict(name=_ident(table_name, "table", table_set), cols=[])
            s = set()
            for k, v in decl.items():
                if k in _TABLE_MODIFIERS:
                    rv[k] = v
                else:
                    try:
                        rv.cols.append(_col_decl(_ident(k, "column", s), v))
                    except Exception as e:
                        pykern.pkinspect.append_exception_reason(
                            e, f"table={table_name} col={k} decl={v}"
                        )
                        raise
            rv.pksetdefault(index=(), unique=())
            return rv

        s = set()
        # parse fully before creating, don't return a generator
        return [_table_decl(k, v, s) for k, v in schema.items()]

    def _table_create(self, spec):
        def _args():
            rv = [spec.name, self._metadata]
            self._primary_keys = []
            for x in spec.cols:
                rv.append(_col(x))
            if not self._primary_keys:
                raise AssertionError(f"table={spec.name} has no primary keys")
            if len(self._primary_keys) == 1:
                # The first table is the default primary key for "foreign" col modifier.
                # It's unlikely there would be two tables with a single primary key with
                # the same name so this is a DWIM feature.
                self._primary_key_cols.pksetdefault(self._primary_keys[0], spec.name)
            return _constraints(
                PKDict({x: list(spec.get(x, [])) for x in _TABLE_MODIFIERS}),
                rv,
            )

        def _col(col_spec):
            a = [col_spec.pkdel("name"), col_spec.pkdel("stype")]
            if a[1] is _PRIMARY_ID_STYPE:
                _col_primary_id(col_spec, a)
            elif col_spec.get("primary_key"):
                self._primary_keys.append(a[0])
            if col_spec.pkdel("foreign"):
                a.append(
                    sqlalchemy.ForeignKey(f"{self._primary_key_cols[a[0]]}.{a[0]}")
                )
                # foreign keys can be nullable so don't set unique implicitly
                if not col_spec.get("primary_key"):
                    col_spec.index = True
            if col_spec.get("unique"):
                col_spec.index = True
            col_spec.pksetdefault(nullable=False)
            return sqlalchemy.Column(*a, **col_spec)

        def _col_primary_id(col_spec, args):
            n = args[0]
            if s := col_spec.pkdel("sequence"):
                if n in self._primary_id_cols:
                    raise AssertionError(
                        f"duplicate primary_id decl column={n} table={spec.name}"
                    )
                self._primary_id_cols.add(n)
                self._primary_keys.append(n)
                # Define for sqlite, too, because it's definition is used above
                args.append(
                    sqlalchemy.Sequence(
                        f"{n}_seq",
                        start=_PRIMARY_ID_INC + s,
                        increment=_PRIMARY_ID_INC,
                    )
                )
                col_spec.primary_key = True
            elif n in self._primary_id_cols:
                col_spec.foreign = True
            else:
                # TODO more flexible some day
                raise AssertionError(
                    f"invalid primary_id or not found foreign id col_spec={args} {col_spec} table={spec.name}"
                )

        def _constraints(modifiers, rv):
            # primary_keys are automatically indexed
            s = set([str(sorted(self._primary_keys))])
            for x in modifiers.foreign:
                # unique and existing index takes precedence
                modifiers.index.append(tuple(x[0]))
                rv.append(sqlalchemy.ForeignKeyConstraint(*x))
            for x in modifiers.unique:
                s.add(str(sorted(x)))
                rv.append(sqlalchemy.UniqueConstraint(*x))
            i = 1
            for x in modifiers.index:
                y = str(sorted(x))
                if y in s:
                    continue
                rv.append(sqlalchemy.Index(f"idx_{spec.name}_{i}", *x))
                i += 1
            return rv

        return _TableWrap(sqlalchemy.Table(*_args()))


# At end to avoid clutter at top
_RESERVED_IN_SQLITE_POSTGRES = frozenset(
    {
        # sqlalchemy word we use so can't be column name
        _NULLABLE_DECL,
        "abort",
        "action",
        "add",
        "after",
        "all",
        "alter",
        "analyze",
        "analyse",
        "and",
        "any",
        "array",
        "as",
        "asc",
        "asymmetric",
        "attach",
        "authorization",
        "autoincrement",
        "before",
        "begin",
        "between",
        "binary",
        "both",
        "by",
        "cascade",
        "case",
        "cast",
        "check",
        "collate",
        "column",
        "commit",
        "concurrently",
        "conflict",
        "constraint",
        "cross",
        "create",
        "current_catalog",
        "current_date",
        "current_role",
        "current_time",
        "current_timestamp",
        "current_user",
        "database",
        "default",
        "deferrable",
        "deferred",
        "delete",
        "desc",
        "detach",
        "distinct",
        "do",
        "drop",
        "each",
        "else",
        "end",
        "escape",
        "except",
        "exclusive",
        "exists",
        "explain",
        "false",
        "fetch",
        "for",
        "foreign",
        "from",
        "full",
        "glob",
        "grant",
        "group",
        "having",
        "if",
        "ignore",
        "immediate",
        "in",
        "index",
        "initially",
        "inner",
        "insert",
        "instead",
        "intersect",
        "into",
        "is",
        "isnull",
        "join",
        "key",
        "leading",
        "left",
        "like",
        "limit",
        "localtime",
        "localtimestamp",
        "match",
        "natural",
        "no",
        "not",
        "notnull",
        "null",
        "of",
        "offset",
        "on",
        "only",
        "or",
        "order",
        "outer",
        "overlaps",
        "plan",
        "placing",
        "pragma",
        "primary",
        "query",
        "raise",
        "recursive",
        "references",
        "regexp",
        "reindex",
        "release",
        "rename",
        "replace",
        "restrict",
        "right",
        "rollback",
        "row",
        "savepoint",
        "select",
        "session_user",
        "set",
        "similar",
        "some",
        "symmetric",
        "table",
        "temp",
        "temporary",
        "then",
        "to",
        "trailing",
        "transaction",
        "trigger",
        "true",
        "union",
        "unique",
        "update",
        "using",
        "user",
        "values",
        "variadic",
        "vacuum",
        "verbose",
        "view",
        "virtual",
        "when",
        "where",
        "window",
        "with",
        "without",
    }
)

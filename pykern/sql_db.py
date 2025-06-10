"""EXPIREMENTAL sqlalchemy wrapper

This interface is going to change.

:copyright: Copyright (c) 2024 The Board of Trustees of the Leland Stanford Junior University, through SLAC National Accelerator Laboratory (subject to receipt of any required approvals from the U.S. Dept. of Energy).  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
import pykern.pkconfig
import pykern.util
import re
import sqlalchemy
import sqlalchemy.sql.operators
import sys

_RESERVED_IN_SQLITE_POSTGRES = frozenset({
    "abort", "action", "add", "after", "all", "alter", "analyze", "analyse", "and", "any",
    "array", "as", "asc", "asymmetric", "attach", "authorization", "autoincrement", "before",
    "begin", "between", "binary", "both", "by", "cascade", "case", "cast", "check", "collate",
    "column", "commit", "concurrently", "conflict", "constraint", "cross", "create", "current_catalog",
    "current_date", "current_role", "current_time", "current_timestamp", "current_user", "database",
    "default", "deferrable", "deferred", "delete", "desc", "detach", "distinct", "do", "drop", "each",
    "else", "end", "escape", "except", "exclusive", "exists", "explain", "false", "fetch", "for",
    "foreign", "from", "full", "glob", "grant", "group", "having", "if", "ignore", "immediate", "in",
    "index", "initially", "inner", "insert", "instead", "intersect", "into", "is", "isnull", "join",
    "key", "leading", "left", "like", "limit", "localtime", "localtimestamp", "match", "natural", "no",
    "not", "notnull", "null", "of", "offset", "on", "only", "or", "order", "outer", "overlaps", "plan",
    "placing", "pragma", "primary", "query", "raise", "recursive", "references", "regexp", "reindex",
    "release", "rename", "replace", "restrict", "right", "rollback", "row", "savepoint", "select",
    "session_user", "set", "similar", "some", "symmetric", "table", "temp", "temporary", "then", "to",
    "trailing", "transaction", "trigger", "true", "union", "unique", "update", "using", "user",
    "values", "variadic", "vacuum", "verbose", "view", "virtual", "when", "where", "window", "with",
    "without"
})

_PRIMARY_ID_DECL = "primary_id"

_STYPE_MAP = PKDict({
    "bool": sqlalchemy.types.Boolean(),
    "date_time": sqlalchemy.types.DateTime(),
    "float 32": sqlalchemy.types.Float(precision=24),
    "float 64": sqlalchemy.types.Float(precision=53),
    "int 32": sqlalchemy.types.Integer(),
    "int 64": sqlalchemy.types.BigInteger(),
    # str & primary_id are special cases
    "text": sqlalchemy.types.Text(),
})

_PRIMARY_ID_INC = 1000

_PRIMARY_ID_MOD = _PRIMARY_ID_INC // 10

o_PRIMARY_ID_STYPE = sqlalchemy.types.BigInteger()

_QUALIFIER = re.compile(r"^\d+$")

_STR_DECL = "str"

# Denormalization is ok since _STYPE_MAP is checked.
_TYPE_NAMES = frozenset({
    "bool", "date_time", "float", "int", _PRIMARY_ID_DECL, _STR_DECL, "text"
})

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
    def __init__(self, uri, decls):
        @pykern.pkconfig.parse_none
        # TODO(robnagler): need to set connection args, e.g. pooling
        self.uri = uri
        self._engine = sqlalchemy.create_engine(uri, echo=_cfg.debug)
        self._table_builder = _TableBuilder(self._engine, decls)
        self._tables = _table_builder.tables
        self._is_sqlite = uri.startswith("sqlite")

    def session(self):
        # is context manager so can be with or not
        # TODO(robnagler) keep track of sessions?
        return _Session(self)


class _Session:
    """Holds SQLAlchemy engine and tables.

    All quests automatically begin a transaction at start and commit
    on success or rollback on an exception.
    """

    def __init__(self, schema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._conn = None
        self._txn = None
        self.schema = schema

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *args, **kwargs):
        self.commit_or_rollback(commit=exc_type is None)

    def column_map(self, table, key_col, value_col, **where):
        return PKDict({r[key_col]: r[value_col] for r in self.select(table, **where)})

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
            args (tuple): if supplied, ``args[0]`` is (shallow) copied to a `PKDict`
            kwargs (dict): additional args are applied to `PKDict`
        Returns:
            PKDict: inserted values with primary_id (if generated)
        """
        m = self.schema._tables[lc(table)]
        v = PKDict(args[0]) if args else PKDict()
        if kwargs:
            v.pkupdate(kwargs)
        v = m.fixup_pre_insert(self, v)
        return m.fixup_post_insert(
            self,
            v,
            getattr(
                self.execute(m.table.insert().values(v)),
                "inserted_primary_key",
                None,
            ),
        )

    def rollback(self):
        self.commit_or_rollback(commit=False)

    def select(self, table_or_stmt, **where):
        def _stmt(table):
            rv = sqlalchemy.select(table)
            if where:
                rv.where(
                    *(
                        sqlalchemy.sql.operators.eq(table.columns[k], v)
                        for k, v in where.items()
                    )
                )
            return rv.limit(500)

        return self.execute(
            _stmt(self.schema._tables[lc(table_or_stmt)].table)
            if isinstance(table_or_stmt, str)
            else table_or_stmt
        )

    def select_max_primary_id(self, table):
        m = self.schema._tables[lc(table)]
        return self.execute(
            sqlalchemy.select(
                sqlalchemy.func.max(m.table.columns[m.primary_id]),
            )
        ).scalar()

    def select_or_insert(self, table, **values):
        if m := self.select_one_or_none(table, **values):
            return m
        return self.insert(table, **values)

    def select_one(self, table_or_stmt, **where):
        if rv := self.select_one_or_none(table_or_stmt, **where):
            return rv
        raise NoRows(table_or_stmt=table_or_stmt, where=where)

    def select_one_or_none(self, table_or_stmt, **where):
        rv = None
        for x in self.select(table_or_stmt, **where):
            if rv is not None:
                raise MoreThanOneRow(table_or_stmt=table_or_stmt, where=where)
            rv = x
        return rv

    def __conn(self):
        if self._conn is None:
            self._conn = self.schema._engine.connect()
            self._txn = self._conn.begin()
        return self._conn


class _TableBuilder:
    """Defines the schema for SQLAlchemy"""

    def __init__(self, engine, decls):
        self.metadata = sqlalchemy.MetaData()
        self.tables = PKDict()
        self._primary_id_cols = PKDict()
        self._parser(decls)
        self.metadata.create_all(bind=engine)

    def _parser(self, decls):

        def _col_decl(name, decl):
            rv = PKDict(kwargs=PKDict(), name=name)
            for d in lc(decl).split(" "):
                if d in ("index", "unique", "nullable"):
                    rv.kwargs[d] = True
                elif _QUALIFIER.search(d):
                    if qualifier in rv:
                        raise AssertionError(f"duplicate qualifier={d} field={name}")
                    rv.stype_qualifier = d
                elif d in _TYPE_NAMES:
                    rv.stype_name = d
                else:
                    raise AssertionError(f"invalid declaration={d} field={name}")
            # put in right form here [name, stype, kwargs)
            rv.stype = _stype(rv, decl)
            return rv

        def _ident(name, name_set, which):
            rv = lc(name)
            if rv in _RESERVED_IN_SQLITE_POSTGRES:
                raise AssertionError(f"{which}={rv} is a reserved word")
            if rv in name_set:
                raise AssertionError(f"{which}={rv} is a duplicate (case insensitive)")
            name_set.add(rv)
            return rv


        def _stype(spec, decl):
            if not (t := spec.pkdel("stype_name")):
                raise AssertionError(f"missing type name col={spec.name} decl={decl}")
            if q := spec.pkdel("stype_qualifier"):
                if t == _STR_DECL:
                    return sqlalchemy.types.String(q)
                if t == _PRIMARY_ID_DECL:
                    if not (0 < q < _PRIMARY_ID_MOD):
                        raise AssertionError(f"{_PRIMARY_ID_DECL} qualifier must be between 0 and {_PRIMARY_ID_MOD}")
                    # SIDE-EFFECT: nested function so limited scope
                    spec.sequence = q
                    return _PRIMARY_ID_STYPE
                if t in _STYPE_MAP:
                    raise AssertionError(f"type={t} does not accept a qualifier={q}")
                t += f" {q}"
            if not (rv := _STYPE_MAP.get(t)):
                raise AssertionError(f"type={t} not found or limited qualifier choices")
            return rv

        def _table_decl(table_name, tables, decl):
            rv = PKDict(name=_ident(table_name, tables, "table"), cols=[])
            u = PKDict()
            for k, v in decl.items():
                if k in ("index", "unique"):
                    rv[k] = v
                else:
                    rv.cols.append(_col_decl(_ident(k, u, "column"), v))
            rv.pksetdefault(index=(), unique=())
            return rv

        return self.tables[n] = _Table(n, _table(n, *args, **kwargs))

    def _table(self, table_name, *cols, index=(), unique=()):
        def _args():
            rv = [table_name, self.metadata]
            for x in cols:
                rv.append(_col_arg(x))
            for x in index:
                rv.append(sqlalchemy.Index(*x))
            for x in unique:
                rv.append(sqlalchemy.UniqueConstraint(*x))
            return rv

        def _col_arg(decl):
            a = [decl.pkdel("name"), decl.pkdel("stype")]
            if decl.stype is _PRIMARY_ID_STYPE:
                _col_primary_id(decl, a)
            if decl.get("unique"):
                decl.index = True
            decl.pksetdefault(nullable=False)
            return sqlalchemy.Column(*a, **decl)

        def _col_primary_id(decl, args):
            n = args[0]
            if s := decl.pkdel("sequence"):
                args.append(
                    sqlalchemy.Sequence(
                        f"{n}_seq",
                        start=PRIMARY_ID_INC + s,
                        increment=PRIMARY_ID_INC,
                    )
                )
                if n in self._primary_id_cols:
                    raise AssertionError(
                        f"duplicate sequence for column={n} table={table_name}"
                    )
                self._primary_id_cols[n] = table_name
                decl.primary_key = True
            elif i := self._primary_id_cols.get(n):
                args.append(sqlalchemy.ForeignKey(f"{i}.{n}"))
                decl.index = True
            else:
                raise AssertionError(f"invalid use of primary_id name={n} decl={decl}")

        return sqlalchemy.Table(*_args())


class _Table:
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

    def __init__(self, name, table):
        self.table = table
        self.name = name
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
        if session.schema._is_sqlite and self.has_primary_id and self.primary_id not in values:
            v = session.select_max_primary_id(self.name)
            values[self.primary_id] = (
                self.primary_id_start if v is None else v + PRIMARY_ID_INC
            )
        return values

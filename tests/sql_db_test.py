"""test sql_db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_PATH = "test.sqlite3"


def test_1():
    # Must be first
    from pykern.pkcollections import PKDict
    from pykern import pkunit, pkdebug

    with pkunit.save_chdir_work() as d:
        m = _meta(d)
        _validate_schema(m)
        _inserts(m)
        _selects(m)


def _inserts(meta):
    with meta.session() as s:
        r = s.insert("t1", a_name="William", a_int=1, a_text="war and peace")
        s.insert(
            "T2",
            t1_id=r.t1_id,
            a_float=3,
            a_double=1e1000,
            a_bigint=int(1e11),
        )
        r = s.insert(
            "T1", dict(a_name="Mildred", a_int=333, a_text="hitch hiker's guide")
        )
        s.insert("t2", dict(t1_id=r.t1_id, a_float=2, a_bigint=222))
        s.insert(s.t.t2, dict(t1_id=r.t1_id, a_float=3, a_bigint=333))


def _meta(dir_path):
    from pykern.pkcollections import PKDict
    from pykern import sql_db

    return sql_db.Meta(
        uri=_uri(dir_path),
        schema=PKDict(
            T1=PKDict(
                t1_id="primary_id 1",
                a_name="str 64",
                a_text="text",
                a_int="int 32",
                created="datetime index",
                unique=(("a_name", "a_text"),),
            ),
            t2=PKDict(
                t2_id="primary_id 2",
                t1_id="primary_id",
                a_float="float 32",
                a_double="float 64 nullable",
                a_bigint="int 64 unique",
                index=(("t1_id", "t2_id"),),
            ),
            t3=PKDict(
                t3_name="str 4 primary_key",
            ),
            t4=PKDict(
                t3_name="str 4 primary_key foreign",
                t4_pk2="str 4 primary_key",
            ),
            t5=PKDict(
                t3_name="str 4 primary_key",
                t4_pk2="str 4 primary_key",
                foreign=((("t3_name", "t4_pk2"), ("t4.t3_name", "t4.t4_pk2")),),
            ),
        ),
    )


def _selects(meta):
    from pykern import pkunit, pkdebug
    import sqlalchemy

    with meta.session() as s:
        r = s.select_one("t1", where=dict(a_name="Mildred"))
        pkunit.pkeq("hitch hiker's guide", r.a_text)
        t1, t2 = s.t.t1, s.t.t2
        r = s.execute(
            sqlalchemy.select(
                t1,
                t2,
            )
            .join(
                t1,
                t2.c.a_bigint == t1.c.a_int,
            )
            .where(
                t1.c.a_int == 333,
            ),
        )


def _uri(d):
    from pykern import sql_db

    return sql_db.sqlite_uri(d.join(_PATH))


def _validate_schema(meta):
    import re, subprocess
    from pykern import pkunit

    # Need to reorder, because sqlite does not keep a consistent order of index output
    t = []
    i = []
    for l in re.split(
        "\s*\n\s*",
        # Assumes in same directory
        subprocess.check_output(["sqlite3", _PATH, ".schema"], text=True),
    ):
        if len(l) <= 0:
            continue
        l += "\n"
        if re.search("^CREATE(?: UNIQUE)? INDEX", l):
            i.append(l)
        else:
            t.append(l)
    pkunit.file_eq("schema.txt", "".join(t + sorted(i)))
    pkunit.pkeq(["t1", "t2", "t3", "t4", "t5"], sorted(meta.t.keys()))
    pkunit.pkeq(meta.t.t1, meta.table("t1"))

"""test sql_db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_PATH = "test.sqlite3"


def test_1():
    from pykern.pkcollections import PKDict
    from pykern import pkunit, sql_db, pkdebug

    with pkunit.save_chdir_work() as d:
        m = sql_db.Meta(
            uri=_uri(d),
            schema=PKDict(
                t1=PKDict(
                    t1_id="primary_id 1",
                    a_name="str 64",
                    a_text="str 1024",
                    created="date_time index",
                    unique=(("a_name", "a_text"),),
                ),
                t2=PKDict(
                    t2_id="primary_id 2",
                    t1_id="primary_id",
                    a_double="float 64 nullable",
                    a_bigint="int 64 unique",
                    index=(("t1_id", "t2_id"),),
                ),
            ),
        )
        _validate_schema()
        with m.session() as s:
            r1 = s.insert("t1", PKDict(a_name="William", a_text="war and peace"))
            r2 = s.insert("t2", t1_id=r1.t1_id, a_double=1e1000, a_bigint=int(1e11))


def _uri(d):
    return "sqlite:///" + str(d.join(_PATH))


def _validate_schema():
    import re, subprocess
    from pykern import pkunit

    # Need to reorder, because sqlite does not keep a consistent order of index output
    t = []
    i = []
    for l in re.split(
        "\s*\n\s*",
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

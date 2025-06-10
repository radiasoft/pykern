"""test sql_db

:copyright: Copyright (c) 2025 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

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
                    # words like this are reserved to can't be field names
                    unique=(("a_name", "a_text"),),
                ),
                t2=PKDict(
                    t2_id="primary_id 2",
                    t1_id="primary_id",
                    a_double="float 64",
                    a_bigint="int 64 unique",
                    index=(("t1_id", "t2_id"),),
                ),
            ),
        )
        with m.session() as s:
            r1 = s.insert("t1", PKDict(a_name="William", a_text="war and peace"))
            r2 = a.insert("t2", t1_id=r1.t1_id, a_double=1e1000, a_bigint=int(1e11))


def _uri(d):
    return "sqlite:///" + str(d.join("test.sqlite3"))

"""test fconf

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_parser():
    from pykern import pkunit, fconf, pkio, pkjson
    from pykern.pkcollections import PKDict
    from pykern.pkdebug import pkdp

    for d in pkunit.case_dirs():
        p = fconf.Parser(
            pkio.sorted_glob("*.py") + pkio.sorted_glob("*.yml"),
            base_vars=(
                PKDict(fconf_test=PKDict(var1=1234)) if d.basename == "1" else None
            ),
        )
        r = p.result
        r.macros = [f'{p.name}({",".join(p.params)})' for p in p.macros.values()]
        pkjson.dump_pretty(r, filename="res.json")


def test_parse_all():
    from pykern import pkunit, fconf, pkjson

    d = pkunit.work_dir().join("parseall").ensure(dir=1)
    d.join("1.yml").write("---\npi: 3.14\ne: 2.7\n")
    d.join("2.yaml").write("---\npi: ${e}\n")
    d.join("3.yml").write("---\ne: 1.6\n")
    d.join("not-seen.yml").write("---\nnot-seen: false\n")
    a = fconf.parse_all(d, glob="?")
    pkjson.dump_pretty(a, filename=d.join("res.json"))
    pkunit.pkok("not-seen" not in a, "not-seen got parsed values={}", a)
    pkunit.pkeq(2.7, a.pi)
    pkunit.pkeq(1.6, a.e)

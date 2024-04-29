"""PyTest for :mod:`pykern.pkyaml`

:copyright: Copyright (c) 2015-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_load_dump():
    """Test values are unicode"""
    from pykern import pkunit
    from pykern import pkyaml

    for d in pkunit.case_dirs():
        y = pkyaml.load_file(d.join("in.yml"))
        _assert_load(y)
        pkyaml.dump_pretty(y, d.join("out.yml"))


def test_load_resource():
    """Test file can be read"""
    from pykern import pkunit
    from pykern import pkyaml

    p1 = pkunit.import_module_from_data_dir("p1")
    pkunit.pkeq(
        "v2",
        p1.y["f2"],
        "Resource should be loaded relative to root package of caller",
    )


def _assert_load(value):
    from pykern.pkunit import pkok, pkfail
    from pykern.pkcollections import PKDict

    if isinstance(value, PKDict):
        for k, v in value.items():
            _assert_load(k)
            _assert_load(v)
    elif isinstance(value, list):
        for v in value:
            _assert_load(v)
    else:
        pkok(
            isinstance(value, (int, float, str)),
            "unknown type={} value={}",
            type(value),
            value,
        )

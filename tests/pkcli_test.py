"""pytest for `pykern.pkcli`

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import pytest


def test_argh_argument_parsing(capsys):
    """Test change in how kwargs are handled.

    Prior to argh v0.30.0 keyword_arg would be an optional flag
    argument So, you could have `arghparsing argh-test kwarg-to-positional x`
    or `pykern argh-test kwarg-to-positional x --keyword-arg foo`.

    In version >= 0.30.0 keyword_arg became an optional positional
    arg. So, you could have `pykern argh-test kwarg-to-positional x`
    or `pykern argh-test kwarg-to-positional x foo`
    But, if you set name_mapping_policy to BY_NAME_IF_HAS_DEFAULT then
    the old bheavior is retained.

    See the argh changelog for more information:
    https://argh.readthedocs.io/en/latest/changes.html#version-0-30-0-2023-10-21
    """
    from pykern.pkunit import pkre, pkeq

    p = "p"
    k = "k"
    pkeq(
        _main(
            "package2",
            [
                "argh_test",
                "kwarg-to-positional",
                p,
                "--keyword-arg",
                k,
            ],
        ),
        0,
    )
    pkre(f"positional_arg={p} keyword_arg={k}", capsys.readouterr()[0])


def test_command_error(capsys):
    from pykern import pkcli
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    with pytest.raises(pkcli.CommandError) as e:
        pkcli.command_error("{abc}", abc="abcdef")
    assert "abcdef" in str(
        e.value
    ), "When passed a format, command_error should output formatted result"
    _deviance(
        "package2", ["some-mod", "command-error"], None, r"raising CommandError", capsys
    )


def test_main1():
    """Verify basic modes work"""
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    rp = "package1"
    _conf(rp, ["conf1", "cmd1", "1"])
    _conf(rp, ["conf1", "cmd2"], first_time=False)
    _conf(rp, ["conf2", "cmd1", "2"])
    _conf(rp, ["conf3", "3"], default_command=True)
    _conf(rp, ["conf4", "99"], default_command=True)
    first_self = _conf(rp, ["conf5", "cmd1", "10"])
    _conf(rp, ["conf5", "cmd1", "3"], first_self=first_self)


def test_main2(capsys):
    from pykern import pkconfig
    import six

    all_modules = r":\nconf1\nconf2\nconf3\nconf4\nconf5\n$"
    pkconfig.reset_state_for_testing()
    rp = "package1"
    _deviance(rp, [], None, all_modules, capsys)
    _deviance(rp, ["--help"], None, all_modules, capsys)
    _deviance(rp, ["conf1"], SystemExit, r"cmd1,cmd2.*too few", capsys)
    _deviance(rp, ["conf1", "-h"], SystemExit, r"\{cmd1,cmd2\}.*commands", capsys)
    _deviance(rp, ["conf5", "-h"], SystemExit, r"\{cmd1\}.*commands", capsys)
    if six.PY2:
        _deviance(rp, ["not_found"], None, r"no module", capsys)
    else:
        _deviance(rp, ["not_found"], ModuleNotFoundError, None, capsys)
    _deviance(rp, ["conf2", "not-cmd1"], SystemExit, r"\{cmd1\}", capsys)


def test_main3():
    """Verify underscores are converted to dashes"""
    from pykern import pkconfig

    pkconfig.reset_state_for_testing()
    assert 0 == _main(
        "package2", ["some-mod", "some-func"]
    ), "some-mod some-func: dashed module and function should work"
    assert 0 == _main(
        "package2", ["some_mod", "some_func"]
    ), "some_mod some-func: underscored module and function should work"


def test_command_info():
    from pykern import pksubprocess
    from pykern.pkunit import case_dirs

    for d in case_dirs("command_info"):
        pksubprocess.check_call_with_signals(
            ["python", d.join("example_pkcli_module.py")],
            output="example_stderr.out",
        )


def _conf(root_pkg, argv, first_time=True, default_command=False, first_self=None):
    from pykern.pkunit import pkeq, pkne, pkok
    import sys

    rv = None
    full_name = ".".join([root_pkg, "pkcli", argv[0]])
    if not first_time:
        pkok(not hasattr(sys.modules, full_name), "module loaded before first call")
    pkeq(0, _main(root_pkg, argv), "Unexpected exit")
    m = sys.modules[full_name]
    if default_command:
        pkeq("default_command", m.last_cmd)
        pkeq(argv[1], m.last_arg)
    else:
        pkeq(argv[1], m.last_cmd)
    if hasattr(m, "last_self"):
        if first_self:
            pkne(first_self, m.last_self)
        else:
            pkok(m.last_self, "")
        rv = m.last_self
    return rv


def _deviance(root_pkg, argv, exc, expect, capsys):
    import re
    from pykern.pkdebug import pkdp
    from pykern import pkunit

    if exc:
        with pytest.raises(exc):
            _main(root_pkg, argv)
        if not expect:
            return
    else:
        assert _main(root_pkg, argv) == 1, f"Failed to exit(1): {argv}"
    out, err = capsys.readouterr()
    if not err:
        err = out
    assert (
        re.search("Args.*arg1", err, flags=re.DOTALL) is None
    ), "failure to ignore arguments and only print subject. out: {}".format(err)
    pkunit.pkre(expect, err)


def _main(root_pkg, argv):
    import sys
    from pykern import pkunit, pkcli

    sys.argv[:] = ["pkcli_test"]
    sys.argv.extend(argv)
    dd = str(pkunit.data_dir())
    try:
        sys.path.insert(0, dd)
        return pkcli.main(root_pkg)
    finally:
        if sys.path[0] == dd:
            sys.path.pop(0)

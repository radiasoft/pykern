"""test pkcli.sphinx

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

_PROJECT = "xyzzy"
_VERSION = "20200202.123456"
_AUTHOR = "Arthur Coder"


def test_build(monkeypatch):
    from pykern import pkunit, pkio

    _mock_metadata(monkeypatch)
    with pkio.save_chdir(pkunit.empty_work_dir().join(_PROJECT).ensure(dir=True)):
        _projex()
        from pykern.pkcli import sphinx

        sphinx.build()
        pkunit.pkre(
            f"{_PROJECT} {_VERSION}", pkio.read_text("_build_html/html/index.html")
        )


def _mock_metadata(monkeypatch):
    from importlib import metadata

    def _mock(*args, **kwargs):
        nonlocal _prev
        if not args or args[0] != _PROJECT:
            return _prev(*args, **kwargs)
        # Do not use PKDict because that's not what metadata returns
        return {
            "Author-email": f"{_AUTHOR} <a@b.c>",
            "Name": _PROJECT,
            "Version": _VERSION,
        }

    _prev = metadata.metadata
    monkeypatch.setattr(metadata, "metadata", _mock)


def _projex():
    from pykern.pkcli import projex
    import subprocess

    subprocess.check_call(("git", "init", "."), stdout=subprocess.DEVNULL)
    projex.init_rs_tree(f"{_PROJECT} for sphinx_test")

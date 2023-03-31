# -*- coding: utf-8 -*-
"""pytest for `pykern.pksetup`

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import subprocess
import contextlib
import glob
import os
import os.path
import py
import pytest
import re
import sys
import tarfile
import zipfile

_TEST_PYPI = "testpypi"


def test_build_clean():
    """Create a normal distribution"""
    from pykern import pkio
    from pykern import pksetup
    from pykern import pkunit

    with _project_dir("pksetupunit1") as d:
        subprocess.check_call(["python", "setup.py", "sdist", "--formats=zip"])
        archive = _assert_members(
            ["pksetupunit1", "package_data", "data1"],
            ["scripts", "script1"],
            ["examples", "example1.txt"],
            ["tests", "mod2_test.py"],
        )
        subprocess.check_call(["python", "setup.py", "build"])
        dat = os.path.join("build", "lib", "pksetupunit1", "package_data", "data1")
        assert os.path.exists(
            dat
        ), "When building, package_data should be installed in lib"
        bin_dir = "scripts-{}.{}".format(*(sys.version_info[0:2]))
        subprocess.check_call(["python", "setup.py", "test"])
        assert os.path.exists("tests/mod2_test.py")
        subprocess.check_call(["git", "clean", "-dfx"])
        assert not os.path.exists(
            "build"
        ), "When git clean runs, build directory should not exist"
        subprocess.check_call(["python", "setup.py", "sdist"])
        pkio.unchecked_remove(archive)
        _assert_members(
            ["!", "tests", "mod2_work", "do_not_include_in_sdist.py"],
            ["tests", "mod2_test.py"],
        )
        # TODO(robnagler) need another sentinel here
        if os.environ.get("PKSETUP_PKDEPLOY_IS_DEV", False):
            subprocess.check_call(["python", "setup.py", "pkdeploy"])


def test_optional_args():
    """Create a normal distribution

    Installs into the global environment, which messes up pykern's install.
    Due to incorrect editing of easy-install.pth.
    """
    from pykern import pkio
    from pykern import pksetup
    from pykern import pkunit
    from pykern import pkdebug

    def _results(pwd, expect):
        x = d.dirpath().listdir(fil=lambda x: x.basename != d.basename)
        pkunit.pkeq(1, len(x))
        a = list(pkio.walk_tree(x[0], "/(civicjson.py|adhan.py|pksetup.*METADATA)$"))
        pkunit.pkeq(expect, len(a))
        for f in a:
            if f.basename == "METADATA":
                return x[0], f
        pkunit.pkfail("METADATA not found in files={}", a)

    with _project_dir("pksetupunit2") as d:
        # clean the work dir then run afind
        subprocess.check_call(
            [
                "pip",
                "install",
                "--root",
                pkunit.work_dir(),
                # No -e or it will modify global environment
                ".[all]",
            ],
        )
        x, m1 = _results(d, 3)
        pkio.unchecked_remove(x, ".git")
        e = os.environ.copy()
        e["PYKERN_PKSETUP_NO_VERSION"] = "1"
        subprocess.check_call(
            [
                "pip",
                "install",
                "--root",
                pkunit.work_dir(),
                ".",
            ],
            env=e,
        )
        _, m2 = _results(d, 1)
        pkunit.pkne(m1, m2)


@contextlib.contextmanager
def _project_dir(project):
    """Copy "data_dir/project" to "work_dir/project"

    Initializes as a git repo.

    Args:
        project (str): subdirectory name

    Returns:
        py.path.local: working directory"""
    from pykern import pkio
    from pykern import pksetup
    from pykern import pkunit

    d = pkunit.empty_work_dir().join(project)
    pkunit.data_dir().join(d.basename).copy(d)
    with pkio.save_chdir(d):
        subprocess.check_call(["git", "init", "."])
        subprocess.check_call(["git", "config", "user.email", "pip@pykern.org"])
        subprocess.check_call(["git", "config", "user.name", "pykern"])
        subprocess.check_call(["git", "add", "."])
        # Need a commit
        subprocess.check_call(["git", "commit", "-m", "n/a"])
        yield d


def _assert_members(*expect):
    arc = glob.glob(os.path.join("dist", "pksetupunit1*"))
    assert 1 == len(arc), "Verify setup.py sdist creates an archive file"
    arc = arc[0]
    m = re.search(r"(.+)\.(zip|tar.gz)$", os.path.basename(arc))
    base = m.group(1)
    if m.group(2) == "zip":
        with zipfile.ZipFile(arc) as z:
            members = z.namelist()
    else:
        with tarfile.open(arc) as t:
            members = t.getnames()
    for member in expect:
        exists = member[0] != "!"
        if not exists:
            member = member[1:]
        m = os.path.join(base, *member)
        assert bool(m in members) == exists, "When sdist, {} is {} from archive".format(
            m,
            "included" if exists else "excluded",
        )
    return arc

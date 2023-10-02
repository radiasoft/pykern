# -*- coding: utf-8 -*-
"""generate files needed for readthedocs

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import copy
import datetime
import subprocess

def run():
    _sphinx_apidoc(
        author="nobody",
        description="nothing",
        name="pykern",
        version="xx.xx",
    )


def _packages(name):
    """Find all packages by looking for ``__init__.py`` files.

    Mostly borrowed from https://bitbucket.org/django/django/src/tip/setup.py

    Args:
        name (str): name of the package (directory)

    Returns:
        list: packages names
    """
    import os

    def _fullsplit(path, result=None):
        """
        Split a pathname into components (the opposite of os.path.join) in a
        platform-neutral way.

        """
        if result is None:
            result = []
        head, tail = os.path.split(path)
        if head == "":
            return [tail] + result
        if head == path:
            return result
        return _fullsplit(head, [tail] + result)

    res = []
    for (
        dirpath,
        _,
        filenames,
    ) in os.walk(name):
        if "__init__.py" in filenames:
            res.append(str(".".join(_fullsplit(dirpath))))
    return res

def _sphinx_apidoc(**kwargs):
    """Call `sphinx-apidoc` with appropriately configured ``conf.py``."""

    def _read(filename):
        """Open and read filename

        Args:
            filename (str): what to read

        Returns:
            str: contents of filename
        """
        with open(filename, "r") as f:
            return f.read()

    def _write(filename, content):
        """Writes a file"""
        with open(filename, "w") as f:
            f.write(content)

    p = _packages(kwargs["name"])

    values = {
        "empty_braces": "{}",
        "packages": p,
        "year": datetime.datetime.now().year,
    }
    values.update(kwargs)

    from pykern import pkresource

    data = _read(pkresource.filename("docs-conf.py.format"))
    _write("docs/conf.py", data.format(**values))
    #subprocess.check_call(
    #    [
    #        "sphinx-apidoc",
    #        "-f",
    #        "-o",
    #        "docs",
    #    ]
    #    + p,
    #)


def _version(base):
    """Get a chronological version from git or PKG-INFO

    Args:
        base (dict): state

    Returns:
        str: Chronological version "yyyymmdd.hhmmss"
        str: git sha if available
    """
    from pykern import pkconfig

    global _cfg

    if not _cfg:
        _cfg = pkconfig.init(no_version=(False, bool, "use utcnow as version"))
    if _cfg.no_version:
        return _version_from_datetime(), None
    v1 = _version_from_pkg_info(base)
    v2, sha = _version_from_git()
    if v1:
        if v2:
            return (v1, None) if float(v1) > float(v2) else (v2, sha)
        return v1, None
    if v2:
        return v2, sha
    raise ValueError("Must have a git repo or an source distribution")


def _version_from_git():
    """Chronological version string for most recent commit or time of newer file.

    Finds the commit date of the most recent branch. Uses ``git
    ls-files`` to find files under git control which are modified or
    to be deleted, in which case we assume this is a developer, and we
    should just use the current time for the version. It will be newer
    than any committed version, which is all we care about for upgrades.

    Args:
        base (dict): state

    Returns:
        str: Chronological version "yyyymmdd.hhmmss"
    """
    if not _git_exists():
        return None, None
    # Under development?
    sha = None
    if len(_git_ls_files(["--modified", "--deleted"])):
        vt = None
    else:
        branch = _check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).rstrip()
        vt = _check_output(["git", "log", "-1", "--format=%ct", branch]).rstrip()
        vt = datetime.datetime.fromtimestamp(float(vt))
        sha = _check_output(["git", "rev-parse", "HEAD"]).rstrip()
    return _version_from_datetime(vt), sha


def _version_from_pkg_info(base):
    """Extra existing version from PKG-INFO if there

    Args:
        base (dict): state

    Returns:
        str: Chronological version "yyyymmdd.hhmmss"
    """
    try:
        d = _read(base["name"] + ".egg-info/PKG-INFO")
        m = re.search(r"Version:\s*{}\s".format(_VERSION_RE), d)
        if m:
            return m.group(1)
    except IOError:
        pass
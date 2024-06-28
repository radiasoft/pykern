"""Wrapper for setuptools.setup to simplify creating of `setup.py` files.

Python `setup.py` files should be short for well-structured projects.
`b_setup.setup` assumes there are directories such as `tests`, `docs`,
`bin`, etc. PyKern Projects use `py.test` so the appropriate `Test`
class is provided by this module.

Example:

    A sample ``setup.py`` script::

        setup(
            name='pyexample',
            description='Some Example app',
            author='Example, Inc.',
            author_email='somebody@example.com',
            url='http://example.com',
        )

Assumptions:

    - GUI and console scripts are
      found automatically by special suffixes ``_gui.py`` and
      ``_console.py``. See ``setup`` documentation for an example.

    - Under git control. Even if you are building an app for the first
      time, you should create the repo first. Does not assume anything
      about the remote (i.e. need not be a GitHub repo).

:copyright: Copyright (c) 2015 Radiasoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# DO NOT import __future__. setuptools breaks with unicode in PY2:
# http://bugs.python.org/setuptools/issue152
# Get errors about package_data not containing wildcards, name not found, etc.

# Import only builtin/standard packages so avoid dependency issues
import copy
import datetime
import distutils.cmd
import distutils.log
import glob
import locale
import os
import os.path
import packaging.version
import re
import setuptools
import setuptools.command.sdist
import setuptools.command.test
import subprocess
import sys

#: The subdirectory in the top-level Python where to put resources
PACKAGE_DATA = "package_data"

#: Where scripts live, you probably don't want this
SCRIPTS_DIR = "scripts"

_VERSION_RE = r"(\d{8}\.\d+)"

_cfg = None


class SDist(setuptools.command.sdist.sdist, object):
    """Fix up a few things before running sdist"""

    def check_readme(self, *args, **kwargs):
        """Avoid README error message. We assert differntly.

        Currently only supports ``README.txt`` and ``README``,
        but we may have ``README.md``.
        """
        pass


def install_requires():
    """Parse requirements.txt.

    Returns:
        dict: parsed requirements.txt
    """
    res = []
    # TODO(robnagler) deprecate this for literal install_requires
    with open("requirements.txt", "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            assert not line.endswith("\\"), "does not support continuation lines"
            res.append(line)
    return res


def setup(**kwargs):
    """Parses `README.*` and `requirements.txt`, sets some defaults, then
    calls `setuptools.setup`.

    Scripts are found by looking for files in the top level package directory
    which end with ``_console.py`` or ``_gui.py``. These files must have a
    function called ``main``.

    Example:
        The file ``pykern_console.py`` might contain::

            def main():
                return 2 + 2

        This would create a program called command line program ``pykern`` which
        would call ``main()`` when invoked.

    Args:
        kwargs: see `setuptools.setup`
    """

    def _assert_package_versions():
        """Raise assertion if another module has installed incompatible versions

        Currently no incompatible versions that need to be asserted. This
        commit has an example of how to code this:

        https://git.radiasoft.org/pykern/commit/28c0b69034dd96785964fd7049cc5d33a5c0b9b5
        """
        pass

    name = kwargs["name"]
    if name != "pykern":
        _assert_package_versions()
    assert (
        type(name) == str
    ), "name must be a str; remove __future__ import unicode_literals in setup.py"
    flags = kwargs["pksetup"] if "pksetup" in kwargs else {}
    if "install_requires" not in kwargs:
        kwargs["install_requires"] = install_requires()
    # If the incoming is unicode, this works in Python3
    # https://bugs.python.org/issue13943
    del kwargs["name"]
    base = {
        "classifiers": [],
        "cmdclass": {
            "sdist": SDist,
        },
        "entry_points": _entry_points(name),
        # These both need to be set
        "name": name,
        "packages": _packages(name),
        "pksetup": flags,
    }
    base = _state(base, kwargs)
    _merge_kwargs(base, kwargs)
    _extras_require(base)
    op = setuptools.setup
    if base["pksetup"].get("numpy_distutils", False):
        import numpy.distutils.core

        op = numpy.distutils.core.setup
    del base["pksetup"]
    op(**base)


def _check_output(*args, **kwargs):
    """Run `subprocess.checkout_output` and convert to str

    Args:
        args (list): pass to subprocess.check_output
    Returns:
        str: Output
    """
    try:
        res = subprocess.check_output(*args, **kwargs)
        if isinstance(res, bytes):
            res = res.decode(locale.getpreferredencoding())
            return res
    except subprocess.CalledProcessError as e:
        if hasattr(e, "output") and len(e.output):
            sys.stderr.write(e.output)
        raise


def _entry_points(pkg_name):
    """Find all *_{console,gui}.py files and define them

    Args:
        pkg_name (str): name of the package (directory)

    Returns:
        dict: Mapping of script names to module:methods
    """
    res = {}
    for s in ["console", "gui"]:
        tag = "_" + s
        for p in glob.glob(os.path.join(pkg_name, "*" + tag + ".py")):
            m = re.search(
                r"^([a-z]\w+)" + tag, os.path.basename(p), flags=re.IGNORECASE
            )
            if m:
                ep = res.setdefault(s + "_scripts", [])
                # TODO(robnagler): assert that 'def main()' exists in python module
                ep.append("{} = {}.{}:main".format(m.group(1), pkg_name, m.group(0)))
    return res


def _extras_require(base):
    """Add "all" to extras_require, if supplied

    Args:
        base (dict): our base params, will be updated
    """
    if not "extras_require" in base:
        return
    er = base["extras_require"]
    if not er or "all" in er:
        return
    all_deps = set()
    for key, deps in base["extras_require"].items():
        # Explicit dependencies are not in all, e.g. ':sys_platform != "win32"'
        if ":" not in key:
            all_deps.update(deps)
    if all_deps:
        er["all"] = all_deps


def _find_files(dirname):
    """Find all files checked in with git and otherwise.

    Asserts git is installed and git repo.

    Args:
        dirname (str): directory

    Returns:
        list: Files to include in package
    """
    if _git_exists():
        res = _git_ls_files(["--others", "--exclude-standard", dirname])
        res.extend(_git_ls_files([dirname]))
    else:
        res = []
        for r, _, files in os.walk(dirname):
            for f in files:
                res.append(os.path.join(r, f))
    return sorted(res)


def _git_exists():
    """Have a git repo?

    Returns:
        bool: True if .git dir exists
    """
    return os.path.isdir(".git")


def _git_ls_files(extra_args):
    """Find all the files under git control

    Will return nothing if package_data doesn't exist or no files in it.

    Args:
        extra_args (list): other args to append to command

    Returns:
        list: Files under git control.
    """
    cmd = ["git", "ls-files"]
    cmd.extend(extra_args)
    out = _check_output(cmd, stderr=subprocess.STDOUT)
    return out.splitlines()


def _merge_kwargs(base, kwargs):
    """Merge custom values into kwargs then update base with kwargs

    Args:
        base (dict): computed defaults
        kwargs (dict): passed in from setup.py
    """
    for k in "cmdclass", "entry_points":
        if not k in kwargs:
            continue
        v = kwargs[k]
        if v:
            base[k].update(v)
        del kwargs[k]
    base.update(kwargs)


def _packages(name):
    """Find all packages by looking for ``__init__.py`` files.

    Mostly borrowed from https://bitbucket.org/django/django/src/tip/setup.py

    Args:
        name (str): name of the package (directory)

    Returns:
        list: packages names
    """

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


def _read(filename):
    """Open and read filename

    Args:
        filename (str): what to read

    Returns:
        str: contents of filename
    """
    with open(filename, "r") as f:
        return f.read()


def _readme():
    """Find the README.*. Prefer README.rst

    Returns:
        str: Name of README
    """
    for which in "README.rst", "README.md", "README.txt":
        if os.path.exists(which):
            return which
    raise ValueError("You need to create a README.rst")


def _remove(path):
    """Remove path without throwing an exception"""
    try:
        os.remove(path)
    except OSError:
        pass


def _state(base, kwargs):
    """Gets version and package_data. Writes MANIFEST.in.

    Args:
        base (dict): our base params

    Returns:
        dict: base updated
    """
    state = {}
    sha = "\n"
    if not "version" in kwargs:
        state["version"], s = _version(base)
        if s:
            sha = "\n\ngit-commit={}\n".format(s)
    manifest = """# OVERWRITTEN by pykern.pksetup every "python setup.py"
include LICENSE
"""
    if os.path.exists("requirements.txt"):
        manifest += "include requirements.txt\n"
    readme = _readme()
    state["long_description"] = _read(readme).rstrip() + sha
    manifest += "include {}\n".format(readme)
    dirs = ["docs", "tests"]
    if "extra_directories" in base["pksetup"]:
        dirs.extend(base["pksetup"]["extra_directories"])
    for which in (PACKAGE_DATA, SCRIPTS_DIR):
        is_pd = which == PACKAGE_DATA
        d = os.path.join(base["name"], which) if is_pd else which
        f = _find_files(d)
        if f:
            if is_pd:
                state[which] = {base["name"]: f}
                state["include_package_data"] = True
            else:
                state[which] = f
            dirs.append(d)
    manifest += "".join(["recursive-include {} *\n".format(d) for d in dirs])
    _write("MANIFEST.in", manifest)
    base.update(state)
    return base


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
    v2, sha = _version_from_git(base)
    if v1:
        if v2:
            return (v1, None) if float(v1) > float(v2) else (v2, sha)
        return v1, None
    if v2:
        return v2, sha
    raise ValueError("Must have a git repo or an source distribution")


def _version_float(value):
    m = re.search(_VERSION_RE, value)
    assert m, "version={} syntax incorrect must match {}".format(value, _VERSION_RE)
    return m.group(1)[: -len(m.group(2))] if m.group(2) else m.group(1)


def _version_from_datetime(value=None):
    # Avoid 'UserWarning: Normalizing' by setuptools
    return str(
        packaging.version.Version(
            (value or datetime.datetime.utcnow()).strftime("%Y%m%d.%H%M%S"),
        ),
    )


def _version_from_git(base):
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


def _write(filename, content):
    """Writes a file"""
    with open(filename, "w") as f:
        f.write(content)

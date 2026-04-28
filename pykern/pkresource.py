"""Where external resources are stored

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Root module: avoid importing modules which import pkconfig
from pykern import pkconst
from pykern import pkinspect
from pykern import pkio
import errno
import glob
import importlib
import os.path
import sys

from pykern.pkdebug import pkdp

if sys.version_info < (3, 10):
    # There's a bug resources.files() in 3.9.15 so need this.
    # Also works with older versions than 3.9
    import pkg_resources

    def _resource_filename(package, path):
        return pkg_resources.resource_filename(
            package,
            os.path.join(pkconst.PACKAGE_DATA, path),
        )

else:
    import importlib.resources

    def _resource_filename(package, path):
        return str(
            importlib.resources.files(package).joinpath(pkconst.PACKAGE_DATA, path)
        )


def file_path(relative_filename, caller_context=None, packages=None):
    """Return the path to the resource

    Args:
        relative_filename (str): file name relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`
        packages (List[str]): Packages to search.

    Returns:
        py.path: absolute path of the resource file
    """
    return pkio.py_path(filename(relative_filename, caller_context, packages))


def filename(relative_filename, caller_context=None, packages=None):
    """Return the filename to the resource

    Args:
        relative_filename (str): file name relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`
        packages (List[str]): Packages to search.

    Returns:
        str: absolute path of the resource file
    """
    assert not os.path.isabs(
        relative_filename
    ), "must not be an absolute file name={}".format(relative_filename)
    a = []
    for f, p in _files(relative_filename, caller_context, packages):
        a.append(p)
        if os.path.exists(f):
            return f
    _raise_no_file_found(a, relative_filename)


def glob_paths(relative_path, caller_context=None, packages=None):
    """Find all paths that match the relative path in all packages

    Args:
        relative_path(str): Path relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`.
        packages (List[str]): Packages to search.
    Returns:
        py.path: absolute paths of the matched files
    """
    r = []
    for f, p in _files(relative_path, caller_context, packages):
        r.extend(glob.glob(f))
    return [pkio.py_path(f) for f in r]


def _files(path, caller_context, packages):

    if caller_context and packages:
        raise ValueError(
            f"Use only one of caller_context={caller_context} and packages={packages}",
        )
    for p in list(
        map(
            lambda m: pkinspect.root_package(importlib.import_module(m)),
            packages
            or [
                pkinspect.root_package(
                    caller_context if caller_context else pkinspect.caller_module()
                )
            ],
        )
    ):
        yield (
            _resource_filename(p, path),
            p,
        )


def _raise_no_file_found(packages, path):
    msg = f"unable to locate in packages={packages}"
    if "__main__" in packages:
        msg += "; do not call module as a program"
    raise IOError(errno.ENOENT, msg, path)

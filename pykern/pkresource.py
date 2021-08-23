# -*- coding: utf-8 -*-
u"""Where external resources are stored

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Root module: Import only builtin packages so avoid dependency issues
import errno
import glob
import importlib
import os.path
import pkg_resources

# TODO(e-carlin): discuss with rn if ok to import pkio
from pykern import pkinspect
from pykern import pkio
from pykern import pksetup


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
    assert not os.path.isabs(relative_filename), \
        'must not be an absolute file name={}'.format(relative_filename)
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
    a = []
    for f, p in _files(relative_path, caller_context, packages):
        a.append(p)
        r.extend(glob.glob(f))
    return [pkio.py_path(f) for f in r]


def _files(path, caller_context, packages):
    if caller_context and packages:
        raise ValueError(
            f'Use only one of caller_context={caller_context} and packages={packages}',
        )
    for p in list(map(
        lambda m: pkinspect.root_package(importlib.import_module(m)),
        packages or \
            [pkinspect.root_package(caller_context if caller_context else pkinspect.caller_module())],
    )):
        # TODO(e-carlin): using pkg_resources is discouraged
        # https://setuptools.readthedocs.io/en/latest/pkg_resources.html
        # But, as of py3.7 importlib.resources doesn't offer a good API
        # for accessing directories
        # https://docs.python.org/3/library/importlib.html#module-importlib.resources
        # https://gitlab.com/python-devs/importlib_resources/-/issues/58
        yield (
            pkg_resources.resource_filename(
                p,
                os.path.join(pksetup.PACKAGE_DATA, path),
            ),
            p,
        )


def _raise_no_file_found(packages, path):
    msg = f'unable to locate in packages={packages}'
    if '__main__' in packages:
        msg += '; do not call module as a program'
    raise IOError(errno.ENOENT, msg, path)

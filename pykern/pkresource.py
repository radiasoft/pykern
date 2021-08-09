# -*- coding: utf-8 -*-
u"""Where external resources are stored

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

# Root module: Import only builtin packages so avoid dependency issues
import errno
import glob as builtin_glob
import importlib
import os.path
import pkg_resources

# TODO(e-carlin): discuss with rn if ok to import pkio
from pykern import pkinspect
from pykern import pkio
from pykern import pksetup


def filename(relative_filename, caller_context=None, additional_packages=None, relpath=False):
    """Return the filename to the resource

    Args:
        relative_filename (str): file name relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`
        additional_packages (List[str]): Packages to search first in addition to caller_module/caller_context
        relpath (bool): If True path is relative to package package_data dir

    Returns:
        str: absolute or relative (to package_data) path of the resource file
    """
    assert not os.path.isabs(relative_filename), \
        'must not be an absolute file name={}'.format(relative_filename)
    a = []
    for f, p in _files(relative_filename, caller_context, additional_packages):
        a.append(p)
        if os.path.exists(f):
            if relpath:
                f = str(pkio.py_path(
                    os.path.join(pkg_resources.resource_filename(p, ''), pksetup.PACKAGE_DATA),
                ).bestrelpath(pkio.py_path(f)))
            return f
    msg = f'unable to locate in packages={a}'
    if '__main__' in a:
        msg += '; do not call module as a program'
    raise IOError(errno.ENOENT, msg, relative_filename)


def glob(relative_path, caller_context=None, additional_packages=None):
    """Find all paths that match the relative path

    Args:
        relative_path(str): Path relative to package_data directory.
        caller_context (object): Any object from which to get the `root_package`.
        additional_packages (List[str]): Packages to search first in addition to caller_module/caller_context
    Returns:
        [str]: absolute paths of the matched files
    """
    res = []
    for f, _ in _files(relative_path, caller_context, additional_packages):
        res.extend(builtin_glob.glob(f))
    return res


def _files(path, caller_context, additional_packages):
    # Search additional_packages first so they can possibly override caller context/module
    # files of the same name
    for p in list(map(
        lambda m: pkinspect.root_package(importlib.import_module(m)),
        additional_packages or [],
    )) + [
        pkinspect.root_package(
            caller_context if caller_context else pkinspect.caller_module(),
        )
    ]:
        # TODO(e-carlin): using pkg_resources is discouraged
        # https://setuptools.readthedocs.io/en/latest/pkg_resources.html
        # But, as of py3.7 importlib.resources doesn't offer a good API
        # for accessing directories
        # https://docs.python.org/3/library/importlib.html#module-importlib.resources
        # https://gitlab.com/python-devs/importlib_resources/-/issues/58
        yield pkg_resources.resource_filename(
            p,
            os.path.join(pksetup.PACKAGE_DATA, path),
        ), p

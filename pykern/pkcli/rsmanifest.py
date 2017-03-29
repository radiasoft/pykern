# -*- coding: utf-8 -*-
u"""Create and read global and user manifests.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

#: Appears in each directory
BASENAME = 'rsmanifest.json'

#POSIT: https://github.com/radiasoft/containers/blob/master/bin/build build_rsmanifest()
#: Written once at build time
CONTAINER_FILE = '/' + BASENAME

#: Format version
FILE_VERSION = '20170217.180000'

#: Read and written multiple times as the run user
USER_FILE = '~/' + BASENAME

# Identifies codes which are not installed in a pyenv
_NO_PYENV = ''


def add_code(name, version, uri, source_d, virtual_env=None, pyenv=None):
    """Add a new code to ~?rsmanifest.json

    Args:
        name (str): name of the package
        version (str): commit or version
        uri (str): repo, source link
        source_d (str): directory containing
        virtual_env (str): DEPRECATED
        pyenv (str): pyenv version
    """
    from pykern import pkcollections
    from pykern import pkio
    from pykern import pkjson
    import datetime
    import json

    fn = pkio.py_path(USER_FILE)
    try:
        values = pkcollections.json_load_any(fn)
    except Exception as e:
        if not (pkio.exception_is_not_found(e) or isinstance(e, ValueError)):
            raise
        values = pkcollections.Dict(
            version=FILE_VERSION,
            codes=pkcollections.Dict({_NO_PYENV: pkcollections.Dict()}),
        )
    if pyenv:
        assert not virtual_env, \
            'only one of pyenv or virtual-env (DEPRECATED)'
    elif virtual_env:
        assert not pyenv, \
            'only one of pyenv or virtual-env (DEPRECATED)'
        pyenv = virtual_env
    if not pyenv:
        pyenv = _NO_PYENV
    v = values.codes.get(pyenv) or pkcollections.Dict()
    v[name.lower()] = pkcollections.Dict(
        installed=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        name=name,
        source_d=source_d,
        uri=uri,
        version=version,
    )
    values.codes[pyenv] = v
    pkjson.dump_pretty(values, filename=fn)


def pkunit_setup():
    """Create rsmanifest files"""
    from pykern import pkjson

    pkjson.dump_pretty(
        {
            'version': FILE_VERSION,
            'image': {
                'type': 'pkunit',
            },
        },
        filename=CONTAINER_FILE,
    )
    add_code('pkunit', '1.1', 'https://pykern.org', '/tmp')


def read_all():
    """Merge all manifests

    Returns:
        dict: merged data
    """
    from pykern import pkio
    from pykern import pkjson

    fn = pkio.py_path(USER_FILE)
    # Both must exist or error
    u = pkjson.load_any(fn)
    c = pkjson.load_any(pkio.py_path(CONTAINER_FILE))
    assert u.version == c.version, \
        '(user.version) {} != {} (container.version)'.format(u.version, c.version)
    # There are "guaranteed" to be no collisions, but if there are
    # we override user.
    c.update(u)
    return c

# -*- coding: utf-8 -*-
u"""Create and read global and user manifests.

:copyright: Copyright (c) 2017 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdp

# Appears in each directory
BASENAME = 'rsmanifest.json'

#POSIT: https://github.com/radiasoft/containers/blob/master/bin/build build_rsmanifest()
# Written once at build time
CONTAINER_FILE = '/' + BASENAME

# Read and written multiple times as the run user
USER_FILE = '~/' + BASENAME

# Identifies codes which are not installed in a virtualenv
_NO_VENV = ''


def add_code(name, version, uri, source_d, virtual_env=None):
    """Add a new code to ~?rsmanifest.json

    Args:
        name (str): name of the package
        version (str): commit or version
        uri (str): repo, source link
        source_d (str): directory containing
        virtual_env (str): name of the virtual_env to qualify
    """
    from pykern import pkcollections
    from pykern import pkio
    import datetime
    import json

    fn = pkio.expand_user_path(USER_FILE)
    try:
        values = pkcollections.json_load_any(fn)
    except Exception as e:
        if not (pkio.exception_is_not_found(e) or isinstance(e, ValueError)):
            raise
        values = pkcollections.Dict(
            version='20170217.180000',
            codes=pkcollections.Dict({_NO_VENV: pkcollections.Dict()}),
        )
    if not virtual_env:
        virtual_env = _NO_VENV
    v = values.codes.get(virtual_env) or pkcollections.Dict()
    v[name.lower()] = pkcollections.Dict(
        installed=datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        name=name,
        source_d=source_d,
        uri=uri,
        version=version,
    )
    values.codes[virtual_env] = v
    fn.write(
        json.dumps(values, indent=4, separators=(',', ': '), sort_keys=True) + "\n",
    )

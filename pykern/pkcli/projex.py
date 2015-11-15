# -*- coding: utf-8 -*-
u"""Manage Python development projects

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import copy
import datetime
import os
import re
import subprocess

import py.path

from pykern import pkcli
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource

#: Default values
DEFAULTS = {
    'year': datetime.datetime.now().year,
    'license': 'apache2',
    'copyright_license_rst':
    ''':copyright: Copyright (c) {year} {author}.  All Rights Reserved.
:license: {license}''',
}


#: Licenses
LICENSES = {
    'agpl3': (
        'http://www.gnu.org/licenses/agpl-3.0.txt',
        'License :: OSI Approved :: GNU Affero General Public License v3',
    ),
    'apache2': (
        'http://www.apache.org/licenses/LICENSE-2.0.html',
        'License :: OSI Approved :: Apache Software License',
    ),
    'gpl2': (
        'http://www.gnu.org/licenses/gpl-2.0.txt',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    ),
    'gpl3': (
        'http://www.gnu.org/licenses/gpl-3.0.txt',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    ),
    'lgpl2': (
        'http://www.gnu.org/licenses/lgpl-3.0.txt',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
    ),
    'lgpl3': (
        'http://www.gnu.org/licenses/lgpl-3.0.txt',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
    ),
    'mit': (
        'http://opensource.org/licenses/MIT',
        'License :: OSI Approved :: MIT License',
    ),
    'proprietary': (
        'PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.',
        'License :: Other/Proprietary License',
    ),
}


def init_rs_tree(description):
    """Initialize defaults for RadiaSoft project tree and call `init_tree`

    `name` is the base name of the current directory.

    `url` is ``https://github.com/radiasoft/<name>``

    Args:
        description (str): one-line summary of project
    """
    name = py.path.local().basename
    init_tree(
        name,
        'RadiaSoft LLC',
        'pip@radiasoft.net',
        description,
        'apache2',
        'https://github.com/radiasoft/' + name,
    )


def init_tree(name, author, author_email, description, license, url):
    """Setup a project tree with: docs, tests, etc., and checkin to git.

    Creates: setup.py, index.rst, project dir, <name>_console.py, etc.
    Overwrites files if they exist without checking.

    Args:
        name (str): short name of the project, e.g. ``pykern``.
        author (str): copyright holder, e.g. ``RadiaSoft LLC``
        author_email (str): how to reach author, e.g. ``pip@pykern.org``
        description (str): one-line summary of project
        license (str): url of license
        url (str): website for project, e.g. http://pykern.org
    """
    assert os.path.isdir('.git'), \
        'Must be run from the root directory of the repo'
    assert not os.path.isdir(name), \
        '{}: already exists, only works on fresh repos'.format(name)
    assert name == py.path.local().basename, \
        '{}: name must be the name of the current directory'.format(name)
    license = license.lower()
    base = pkresource.filename('projex')
    values = copy.deepcopy(DEFAULTS)
    values.update({
        'name': name,
        'author': author,
        'description': description,
        'author_email': author_email,
        'url': url,
        'license': _license(license, 0),
        'classifier_license': _license(license, 1),
    })
    values['copyright_license_rst'] = values['copyright_license_rst'].format(**values)
    suffix_re = r'\.jinja$'
    for src in pkio.walk_tree(base, file_re=suffix_re):
        dst = py.path.local(src).relto(str(base))
        dst = dst.replace('projex', name).replace('dot-', '.')
        dst = re.sub(suffix_re, '', dst)
        pkio.mkdir_parent_only(dst)
        _render(src, values, output=dst)
    src = py.path.local(pkresource.filename('projex-licenses'))
    src = src.join(license + '.jinja')
    _render(src, values, output='LICENSE')


def _license(name, which):
    """Returns matching license or command_error"""
    try:
        return LICENSES[name][which]
    except KeyError:
        pkcli.command_error(
            '{}: unknown license name. Valid licenses: {}',
            name,
            ' '.join(sorted(LICENSES.values())),
        )

def _render(*args, **kwargs):
    """Renders the template and adds to git"""
    pkjinja.render_file(*args, **kwargs)
    subprocess.check_call(['git', 'add', kwargs['output']])

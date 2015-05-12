# -*- coding: utf-8 -*-
u"""Manage Python development projects

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function, unicode_literals
from io import open

import os.path


def sphinx_quickstart():
    """Call `sphinx.quickstart.generate` with appropriate default parameters.

    Will create ``docs`` directory with ``source`` directory.    Creates ``.gitignore``.
    """
    assert not os.path.isdir('docs/source')
    """
sphinx-quickstart --quiet --sep --project=pykern --author='RadiaSoft LLC' -v 3.13 --ext-autodoc --ext-intersphinx --ext-todo --ext-mathjax --ext-ifconfig --ext-viewcode --makefile --batchfile docs
docs/source/conf.py
import datetime
version = datetime.datetime.utcnow().strftime('%Y%m%d.%H%M%S')
# The full version, including alpha/beta/rc tags.
release = version

#copyright = u'RadiaSoft LLC'
author = u'RadiaSoft LLC'

extensions = [
    'sphinx.ext.napoleon',

    subprocess.check_call([
        'sphinx-quickstart',
        '--quiet',
        '--project=' + base['name'],
        '--author=' + base['author'],
        '-v',
        base['version'],
        '--release=' + base['version'],
        '--ext-autodoc',
        '--ext-intersphinx',
        '--ext-todo',
        '--ext-mathjax',
        '--ext-ifconfig',
        '--ext-viewcode',
        '--makefile',
        '--batchfile',
        'docs',
    ])


"""

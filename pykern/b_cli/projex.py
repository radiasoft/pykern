# -*- coding: utf-8 -*-
"""Manage Python development projects

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""
from __future__ import print_function
import os.path

def sphinx_quickstart():
    """Call `sphinx.quickstart.generate` with appropriate default parameters.

    Will create ``docs`` directory with ``source`` directory.    Creates ``.gitignore``.
    """
    assert not os.path.isdir('docs/source')

# -*- coding: utf-8 -*-
u"""Simplify rendering jinja2

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import jinja2

from pykern import pkinspect
from pykern import pkio
from pykern import pkresource


def render_file(filename, values, output=None):
    """Render filename as template with values.

    Args:
        basename (str): name without jinja extension
        values (dict): how to replace values
        output (str): file name of output; if None, return str

    Returns:
        str: rendered template
    """
    t = pkio.read_text(filename)
    je = jinja2.Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    res = je.from_string(t).render(values)
    if output:
        pkio.write_text(output, res)
    return res


def render_resource(basename, *args, **kwargs):
    """Render a pkresource as a jinja template.

    Args:
        basename (str): name without jinja extension
        args (list): see func:`render_file` for rest of args and return
    """
    return render_file(
        pkresource.filename(basename + '.jinja', pkinspect.caller_module()),
        *args,
        **kwargs
    )

"""Test pkcli to handle argh breaking changes

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict


def kwarg_to_positional(positional_arg, keyword_arg=None):
    return PKDict(positional_arg=positional_arg, keyword_arg=keyword_arg)

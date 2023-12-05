"""Test pkcli to handle argh breaking changes

Release that caused the breakage https://argh.readthedocs.io/en/latest/changes.html#version-0-30-0-2023-10-21

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict


def kwarg_to_positional(positional_arg, keyword_arg=None):
    """Test change in how kwargs are handled.

    Prior to argh v0.30.0 keyword_arg would be an optional flag
    argument So, you could have `pykern argh-test kwarg-to-positional
    x` or `pykern argh-test kwarg-to-positional x --keyword-arg foo`.

    In version >= 0.30.0 keyword_arg became an optional positional
    arg. So, you could have `pykern argh-test kwarg-to-positional x`
    or `pykern argh-test kwarg-to-positional x foo`

    But, if you set name_mapping_policy to BY_NAME_IF_HAS_DEFAULT then
    the old bheavior is retained.
    """
    return PKDict(positional_arg=positional_arg, keyword_arg=keyword_arg)

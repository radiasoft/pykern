# -*- coding: utf-8 -*-
u"""Demonstrates a RadiaSoft style module.

This module demonstrates how we code at RadiaSoft.  In general
we follow the `Google Python Style Guide
<http://google.github.io/styleguide/pyguide.html>`_ and the
`Sphinx Napoleon Google Docstrings Example <http://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html>`_.

Some Rules:
    We adhere to PEP8 unless overruled by Google's Style Guide or
    explicit rules such as:

    1. Indent by four (4) spaces and no tabs.
    #. Avoid lines over 80 characters. Not everybody's laptop
       can show two 80+ char pages side by side.
    #. All modules are Python 2 and 3 compatible.
    #. Modules are divided into groups of declarations: public constants,
       private constants, public global variables, private global
       variables, public classes, private classes, public functions,
       and private functions. Within each group, the declarations are
       sorted alphabetically.
    #. Logs, exceptions and assertions contain values, not
       just messages. If a value is in error, include it in the
       message along with the expected value, range, etc.
    #. `:func:pykern.pkdebug.pkdp` to print logging messages,
       and `:func:pykern.pkdebug.pkdc` to print trace messages.
    #. Configuration is specified by `:mod:pykern.pkconfig`.
    #. Use single quotes for strings. Use double quotes for docstrings.
    #. TODO(robnagler) is how we represent things to do in a comment

Docstrings begin and end with three double quotes ("). On the line
with the beginning double quotes, you write a one line summary
of the function, class, or module.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
# Imports are sorted alphabetically
# pykern imports are "from" since all modules begin with "pk" so they are unique
from pykern import pkconfig
# Import pkdc and pkdp functions directly. Mostly we import modules and
# qualify uses
from pykern.pkdebug import pkdc, pkdp

# We don't follow PEP8 here. Global variables/constants are separated by one blank
# line.
#: First constant is first alphabetically
ONE = 1

#: Another constant
ZIPPITY = 'doodah'

# Private constant is not documented with '#:'
_SSSHHH = 39

#: The module's config is a public variable. It is initialized at the end.
cfg = None

# Something private isn't publicly documented.
_priv_var = 123


# Two blank lines between functions and classes at the global level
class EMA(object):
    """Exponential moving average

    Used as a demonstration of numerical computations. We document
    the __init__ method at the class level, since it is an
    implicit function call.

    Args:
        length (int): iterations

    Attributes:
        average (float): current value of the average
        length (int): time period
    """
    def __init__(self, length):
        self.length = int(length)
        assert length > 0, \
            '{}: length must be greater than 0'.format(length)
        self._alpha = 2.0 / (float(length) + 1.0)
        self.average = None

    def compute(self, value):
        """Compute the next value in the average

        Args:
            value (float): next number in the average

        Returns:
            float: current value of the average
        """
        if self.average is None:
            self.average = value
        else:
            self.average += self._alpha * (value - self.average)
        return self.average

    def value(self):
        """Get the average

        Returns:
            float: current value of the average
        """
        assert self.average is not None, \
            'self.average is None and has not been initialized'
        return self.average

def _Privy(object):
    """This is a private class that does nothing"""
    pass


def _cfg_length(anything):
    """Configuration parser for any_length

    Args:
        anything (object): configured value

    Returns:
        int: value between 1 and 999
    """
    anything = int(anything)
    assert 0 < anything <= 999, \
        '{}: any_length must be from 1 to 999'
    return anything


# Finally we assign any length. Note that we include a trailing , at the
# end of every line in a list so that you don't have to remember to
# add the comma when you add another line.
cfg = pkconfig.init(
    any_length=(1, _cfg_length, 'A length used by this module'),
)

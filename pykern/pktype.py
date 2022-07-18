# -*- coding: utf-8 -*-
"""Validated types

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern import pkconfig
from pydantic import BaseModel
import typing


class Base:
    def validate(self, val):
        # require override?
        # assert 0, 'subclass must override validate()'
        return val


class PKBoolean(Base):
    def validate(self, val):
        assert isinstance(val, bool)
        return val


class PKChoices:
    def __init__(self, choices):
        self.choices = frozenset(choices)

    def validate(self, val):
        assert val in self.choices, ValueError(f"value={val} not in {self.choices}")
        return val


Float = typing.TypeVar("Float", bound=float)


class PKFloat(Base):
    def validate(self, val):
        return float(val)


class PKInt(Base):
    def validate(self, val):
        assert isinstance(val, int)
        return val


class PKRangedInt(PKInt):
    # py3 has no limits on ints
    def __init__(self, min_val=None, max_val=None):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, val):
        v = super().validate(val)
        assert (self.min_val is None or v >= self.min_val) and (
            self.max_val is None or v <= self.max_val
        )
        return v


class PKRangedFloat(PKFloat):
    import sys

    def __init__(self, min_val=sys.float_info.min, max_val=sys.float_info.max):
        self.min_val = min_val
        self.max_val = max_val

    def validate(self, val):
        assert self.min_val <= super().validate(val) <= self.max_val, ValueError(
            f"value={val} outside of range [{self.min_val}, {self.max_val}]"
        )
        return val


class PKString(Base):
    def validate(self, val):
        assert isinstance(val, pkconfig.STRING_TYPES), ValueError(
            "value={} is not a string".format(val)
        )
        return val


# what would "validate" mean for a struct? What makes this different from a dict?
class PKStruct(Base):
    def __init__(self, **kwargs):
        super(PKStruct, self).__init__(**kwargs)
        self.values = PKDict()

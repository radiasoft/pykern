# -*- coding: utf-8 -*-
"""Validated types

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pydantic
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
from typing import Union


class Base(pydantic.BaseModel):
    val: None


class Boolean(Base):
    val: bool


class Choices(Base):
    choices: frozenset
    val: str

    @pydantic.root_validator
    def validate_val(cls, values):
        d = PKDict(values)
        assert d.val in d.choices, ValueError(f"val={d.val} not in {d.choices}")
        return values


class Float(Base):
    val: pydantic.confloat(strict=True)


class Int(Base):
    val: pydantic.conint(strict=True)


class RangedInt(Int):
    min_val: Union[int, None]
    max_val: Union[int, None]

    @pydantic.root_validator
    def validate_val(cls, values):
        d = PKDict(values)
        _validate_range(d.val, d.min_val, d.max_val)
        return values


class RangedFloat(Float):
    min_val: Union[float, None]
    max_val: Union[float, None]

    @pydantic.root_validator
    def validate_val(cls, values):
        d = PKDict(values)
        _validate_range(d.val, d.min_val, d.max_val)
        return values


class String(Base):
    val: str = ""


def _validate_range(val, min_val, max_val):
    assert (min_val is None or val >= min_val) and (max_val is None or val <= max_val),\
        ValueError(f"val={val} out of range [{min_val},{max_val}]")



# -*- coding: utf-8 -*-
"""Provides useful extensions for :class:`argparse.Namespace`

For now just adds iteration.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkdebug import pkdc, pkdp

import argparse

class Namespace(argparse.Namespace):
    """Adds iteration by returning dict from __iter__
    """
    def __delitem__(self, key):
        """Delete the attr"""
        try:
            delattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __getitem__(self, key):
        """Get the attr"""
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self):
        """ Returns vars()"""
        return iter(vars(self))

    def __len__(self):
        """Length of vars()"""
        return len(vars(self))

    def __setitem__(self, key, value):
        """Set a new or existing key"""
        setattr(self, key, value)

    def update(self, container):
        """Add or replace values from container

        Args:
            container (object): Implements iter and getitem
        """
        for k in container:
            self[k] = container[k]

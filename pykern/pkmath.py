# -*- coding: utf-8 -*-
u"""Simple mathematical operations

Currently this module is used for demonstrating coding and testing
guidelines.

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function


class EMA(object):
    """Exponential moving average

    Used as a demonstration of numerical computations.

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

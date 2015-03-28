# -*- coding: utf-8 -*-
"""Command line process for PyKern

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import sys

import pybivio.cli


def main():
    return pybivio.cli.main('pykern')


if __name__ == '__main__':
    sys.exit(main())

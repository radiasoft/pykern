# -*- coding: utf-8 -*-
"""Startup app for PyKern

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import sys

import pykern.pykern_console


def main():
    sys.argv.insert(1, 'boot', 'gui')
    return pykern.pykern_console.main()


if __name__ == '__main__':
    sys.exit(main())

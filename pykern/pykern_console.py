# -*- coding: utf-8 -*-
"""Front-end command line for `pykern.cli`.

Example:

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import sys

import pykern.cli


def main():
    return pykern.cli.main('pykern')


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""Front-end command line for :mod:`private`.

See :mod:`pykern.pkcli` for how this module is used.

:copyright: Copyright (c) 2024 James Bond.  All Rights Reserved.
:license: PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
"""
import pykern.pkcli
import sys


def main():
    return pykern.pkcli.main("private")


if __name__ == "__main__":
    sys.exit(main())

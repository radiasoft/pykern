# -*- coding: utf-8 -*-
"""PyKern Darwin build file

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import cx_Freeze

bdist_dmg = dict(
    volume_label='PyKern',
    applications_shortcut=True,
)

build_exe = dict(
    packages = ['pykern'], excludes = [], includes=[],
)

bdist_mac = dict(
    bundle_name='PyKern',
)

gui = None
if sys.platform == "win32":
    gui = "Win32GUI"
        
executables = [
    # First executable is what maps to ".app"
    cx_Freeze.Executable('pykern/boot_gui.py', targetName='boot-pykern', base=gui),
    cx_Freeze.Executable('pykern/pykern_console.py', targetName='pykern'),
]

cx_Freeze.setup(
    name='pykern',
    version='0.0.1',
    description='PyKern is an open-source framework for the RadiaSoft Cloud',
    options = dict(
        build_exe=build_exe,
        bdist_mac=bdist_mac,
        bdist_dmg=bdist_dmg,
    ),
    executables=executables,
)

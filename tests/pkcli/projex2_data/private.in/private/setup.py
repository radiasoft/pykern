# -*- coding: utf-8 -*-
"""private setup script

:copyright: Copyright (c) 2024 James Bond.  All Rights Reserved.
:license: PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.
"""
import pykern.pksetup

pykern.pksetup.setup(
    name="private",
    author="James Bond",
    author_email="007@example.com",
    description="Q's super private project",
    install_requires=[
        "pykern",
    ],
    entry_points={
        "console_scripts": ["qdev=private.qdev:main"],
    },
    license="PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.",
    url="https://example.com/jb",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python",
        "Topic :: Utilities",
    ],
)

# -*- coding: utf-8 -*-
"""xyzzy1 setup script

:copyright: Copyright (c) 2024 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import pykern.pksetup

pykern.pksetup.setup(
    name="xyzzy1",
    author="RadiaSoft LLC",
    author_email="pip@radiasoft.net",
    description="a magic trick in adventure",
    install_requires=[
        "pykern",
    ],
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    url="https://github.com/radiasoft/xyzzy1",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python",
        "Topic :: Utilities",
    ],
)

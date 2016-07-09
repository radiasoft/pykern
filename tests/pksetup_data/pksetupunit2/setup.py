# -*- coding: utf-8 -*-
u"""pksetupunit2 setup script

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
try:
    import pykern.pksetup
except ImportError:
    import pip
    pip.main(['install', 'pykern'])
    import pykern.pksetup

pykern.pksetup.setup(
    name='pksetupunit2',
    author='RadiaSoft LLC',
    author_email='pip@radiasoft.net',
    description='optional args like extras_require',
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    url='https://github.com/radiasoft/pksetupunit2',
    extras_require={
        # Something that won't have already been installed
        'r1': ['adhan'],
        'r2': ['civicjson'],
    },
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ],
)

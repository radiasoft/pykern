# -*- coding: utf-8 -*-
"""Install PyKern

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pksetup import setup

setup(
    name='pykern',
    description='Python application support',
    author='RadiaSoft LLC',
    author_email='pip@pykern.org',
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    url='http://pykern.org',
    extras_require={
        'jupyterhub': [
            # Really want git versions, but this fmt is invalid:
            # git+git://github.com/jupyterhub/jupyterhub
            # git+git://github.com/jupyterhub/dockerspawner
            # git+git://github.com/jupyterhub/oauthenticator
            'jupyterhub',
            'dockerspawner',
            'oauthenticator',
        ],
    },
    entry_points={
        'pytest11': ['pykern = pykern.pytest_plugin'],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Utilities',
    ],
)

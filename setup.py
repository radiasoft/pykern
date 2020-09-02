# -*- coding: utf-8 -*-
"""Install PyKern

:copyright: Copyright (c) 2015-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pksetup import setup

setup(
    name='pykern',
    description='Python application support',
    author='RadiaSoft LLC',
    author_email='pip@pykern.org',
    install_requires=[
        'argh>=0.26',
        'future>=0.14',
        'github3.py>=1.1',
        'jinja2>=2.7',
        'psutil>=5.0',
        'py-cpuinfo>=0.2',
        'py>=1.4',
        'pytest>=2.7',
        'pytz>=2015.4',
        'ruamel.yaml>=0.16.0',
        'requests>=2.18',
        'setuptools>=20.3',
        'six>=1.9',
        'Sphinx>=1.3.5',
        'twine>=1.9',
        'tox>=1.9',
        'path.py>=7.7.1',
        'python-dateutil>=2.4.2',

        # for tox
        'pluggy>=0.12.0',
    ],
    license='http://www.apache.org/licenses/LICENSE-2.0.html',
    url='http://pykern.org',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Application Frameworks',
        'Topic :: Utilities',
    ],
)

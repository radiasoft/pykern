# -*- coding: utf-8 -*-
try:
    import pykern.pksetup
except ImportError:
    import pip
    pip.main(['install', 'pykern'])
    import pykern.pksetup

pykern.pksetup.setup(
    name='pksetupunit1',
    description='pksetup Conformance One',
    author='RadiaSoft LLC.',
    author_email='pip@pykern.org',
    url='http://pykern.org',
    pksetup={
        'extra_directories':['examples'],
    },
)

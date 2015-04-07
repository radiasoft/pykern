# -*- coding: utf-8 -*-
"""Startup app for PyKern. Installs the kernel.

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: Apache, see LICENSE for more details.
"""

import sys

import pybivio.platform

#: Which user invoked the boot GUI.
_UID_ARG = 'original_uid:'

def main():
    if pybivio.platform.is_darwin():
        return _darwin(args)
    _unsupported_system()


sys.executable, sys.argv[0], 
def _darwin(args):
    if _darwin_
    uid = os.getuid()
    if uid != 0:
        return _darwin_escalate_privileges(uid)
    _
    os.system('''osascript -e 'display alert "Installing PyKern" as informational' ''')
    import urllib2
    response = urllib2.urlopen('https://pykern.radtrack/')
    html = response.read(timeout=60)


def _darwin_escalate_privileges(uid):
    """Escalate privileges to administrator with Apple Script.

    Args:
        uid (int): original user's id
    """
    cmd = '''osascript -e 'do shell script "{} {}{}" with administrator privileges' '''
    os.system(cmd.format(sys.argv[0], _UID_ARG, uid))


def _unsupported_system():
    """Cannot continue. Platform support not implemented"""
    sys.stderr.write('Unsupported system. Please email support@radtrack.org\n')
    sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())

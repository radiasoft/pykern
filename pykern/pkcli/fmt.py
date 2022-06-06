from pykern.pkdebug import pkdp
import pykern.pksubprocess


def edit(path):
    cmd = ['black', f'{path}']
    pkdp(pykern.pksubprocess.check_call_with_signals(cmd))

def diff(path):
    cmd = ['git', 'diff', f'{path}']
    edit(path)
    pkdp(pykern.pksubprocess.check_call_with_signals(cmd))
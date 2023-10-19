from pykern import pkconfig
from pykern import pkio
import os


def parser(v):
    if not os.path.isabs(v):
        pkconfig.raise_error("Must be absolute")
    if not os.path.isdir(v):
        pkconfig.raise_error("Must be a directory and exist")
    return pkio.py_path(v)

cfg = pkconfig.init(
    # root=("tortilla", parser, "where database resides"),
    root=("/home/vagrant/src/tortilla", parser, "where database resides"),
)
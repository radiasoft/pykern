from pykern import pkconfig
from pykern import pkio
import os


def _parser(value):
    if value == False:
        pkconfig.raise_error("Error prefix")

cfg = pkconfig.init(
    x=(False, _parser, "will error"),
)

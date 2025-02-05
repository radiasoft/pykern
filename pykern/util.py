"""Support routines, including run dir resolution.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Root module: avoid global pykern imports
import os.path
import sys

_ACCEPTABLE_CONTROL_CODE_RATIO = 0.33
_DEFAULT_ROOT = "run"
_DEV_ONLY_FILES = ("setup.py", "pyproject.toml")
_VALID_ASCII_CONTROL_CODES = frozenset((0x7, 0x8, 0x9, 0xA, 0xB, 0xC, 0xD, 0x1B))

_dev_run_dir = None


class APIError(Exception):
    """Application level errors or exceptions sent to client and raised on client"""

    def __init__(self, fmt, *args, **kwargs):
        from pykern.pkdebug import pkdformat

        super().__init__(pkdformat(fmt, *args, **kwargs) if args or kwargs else fmt)


def cfg_absolute_dir(value):
    """Parser function for absolute dir config value

    Args:
        value (str): string absolute path to dir

    Returns:
        py.path.Local absolute path to dir
    """
    from pykern import pkio, pkconfig

    if not os.path.isabs(value):
        pkconfig.raise_error("must be absolute")
    if not os.path.isdir(value):
        pkconfig.raise_error("must be a directory and exist")
    return pkio.py_path(value)


def dev_run_dir(package_object):
    """Resolves run directory if in development mode and creates it if it doesn't exist.

    Note that this assumes a file structure like pykern's where <project_name>'s __init__.py
    lives in <project_name>/<project_name>/

    Args:
        package_object (object): A python object whose root package we are resolving the run directory for

    Returns:
        py.path.local: The absolute path to the run directory.

    Raises:
        AssertionError: Raised when not in development mode
    """
    global _dev_run_dir

    from pykern import pkconfig

    def _check_dev_files(root):
        """Check for files that only exist in development"""
        return any([root.join(f).check() for f in _DEV_ONLY_FILES])

    def _mkdir():
        from pykern import pkinspect, pkio, pkunit

        if pkunit.is_test_run():
            return pkunit.work_dir()
        r = (
            pkio.py_path(
                sys.modules[pkinspect.root_package(package_object)].__file__,
            )
            .dirpath()
            .dirpath()
        )
        if not _check_dev_files(r):
            # Don't run from an install directory
            r = pkio.py_path()
        return pkio.mkdir_parent(r.join(_DEFAULT_ROOT))

    if _dev_run_dir:
        return _dev_run_dir
    if not pkconfig.in_dev_mode():
        raise AssertionError("run dir root must be configured except in dev")
    _dev_run_dir = _mkdir()
    return _dev_run_dir


def is_pure_text(value, is_truncated=False):
    """Guesses if value is text data using heuristics:

    Checks if value can be utf-8 decoded.

    If fails to decode and is_truncated, probes backwards up to 4 chars
    (4 is maximum length of a utf-8 char) in case a valid utf-8
    char was truncated at the boundary of value.

    Returns False if null byte is present.

    On successful decode, checks that the amount of control codes not
    typical of text data do not exceed one third of the total characters.

    Args:
        value (bytes): bytes data
        is_truncated (bool): whether or not value has been truncated

    Returns:
        bool: True if bytes_data is likely pure text, false if likely binary
    """

    def _is_accepted_control_code_ratio(text_value):
        n = 0
        for c in text_value:
            if ord(c) == 0:
                return False
            if ord(c) < 32 and ord(c) not in _VALID_ASCII_CONTROL_CODES:
                n += 1
        return (n / len(text_value)) < _ACCEPTABLE_CONTROL_CODE_RATIO

    def _try_utf8(chunk):
        try:
            return chunk.decode("utf-8", "strict")
        except UnicodeDecodeError:
            return False

    def _utf8_decoded(value):
        if not is_truncated:
            return _try_utf8(value)
        b = value[: len(value)]
        for _ in range(4):
            if d := _try_utf8(b):
                return d
            if len(b) <= 1:
                return False
            b = b[:-1]
        return False

    if value == b"":
        return True
    if d := _utf8_decoded(value):
        return _is_accepted_control_code_ratio(d)
    return False


def random_base62(length=16):
    """Returns a safe string of sufficient length to be a nonce.

    The default is 62^16, which is 4e28. For comparison, 2^64 is 1e19 and
    2^128 is 3e38.

    Args:
        length (int): how long to make the base62 string [16]
    Returns:
        str: random base62 characters
    """
    from pykern import pkconst
    import random

    r = random.SystemRandom()
    return "".join(r.choice(pkconst.BASE62_CHARS) for x in range(length))


def unbound_localhost_tcp_port(start=10000, stop=20000):
    """Looks for AF_INET SOCK_STREAM port for which bind succeeds

    Args:
        start (int): first port [10000]
        stop (int): one greater than last port (passed to range) [20000]
    Returns:
        int: port is available or raises ValueError
    """
    import random, socket
    from pykern import pkasyncio, pkconst

    def _check_port(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((pkconst.LOCALHOST_IP, int(port)))
        return port

    for p in random.sample(range(start, stop), 100):
        try:
            return _check_port(p)
        except Exception:
            pass
    raise ValueError(
        f"unable find port random sample range={start}-{stop} tries=100 ip={pkconst.LOCALHOST_IP}"
    )

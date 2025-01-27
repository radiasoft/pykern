"""Helper functions for to :mod:`inspect`.

:copyright: Copyright (c) 2015 RadiaSoft, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

# Avoid pykern imports so avoid dependency issues for pkconfig
from pykern.pkcollections import PKDict
import importlib
import inspect
import os
import os.path
import pkgutil
import re
import sys

#: Used to simplify paths output
_start_dir = ""
try:
    _start_dir = os.getcwd()
except Exception:
    pass


_VALID_IDENTIFIER_RE = re.compile(r"^[a-z_]\w*$", re.IGNORECASE)


class Call(PKDict):
    """Saves file:line:name of stack frame and renders as string.

    Args:
        frame_or_log (frame or LogRecord): values to extract

    Attributes:
        filename (str): full path (co_filename)
        lineno (int): line number (f_lineno)
        name (str): function name (co_name)
    """

    def __init__(self, frame_or_log):
        try:
            if hasattr(frame_or_log, "f_code"):
                super(Call, self).__init__(
                    filename=frame_or_log.f_code.co_filename,
                    lineno=frame_or_log.f_lineno,
                    name=frame_or_log.f_code.co_name,
                    # Only used by caller_module()
                    _module=sys.modules.get(frame_or_log.f_globals.get("__name__")),
                )
            else:
                super(Call, self).__init__(
                    filename=frame_or_log.pathname,
                    lineno=frame_or_log.lineno,
                    name=frame_or_log.funcName,
                    _module=None,
                )
        finally:
            if frame_or_log:
                del frame_or_log

    def __str__(self):
        try:
            filename = os.path.relpath(self.filename, _start_dir)
            if len(filename) > len(self.filename):
                # "relpath" always makes relative even when no common components.
                # Take the absolute (shorter) path
                filename = self.filename
            return "{}:{}:{}".format(filename, self.lineno, self.name)
        except Exception:
            return "<no file>:0:<no func>"


def append_exception_reason(exc, reason):
    """Augment `exc` with `reason`

    Modifies `exc` in place by adding to `exc.args` or
    `exc.reason`. Does it's best to not cause another exception during
    this process.

    Args:
        exc (BaseException): what was raised
        reason (str): our related reason

    """

    def _prefix_reason(string):
        return ("; " if len(string) > 0 else "") + reason

    if hasattr(exc, "reason") and isinstance(exc.reason, str):
        exc.reason += _prefix_reason(exc.reason)
    if hasattr(exc, "args"):
        if exc.args is None:
            exc.args = tuple()
        if isinstance(exc.args, (tuple, list)):
            if len(exc.args) == 0:
                exc.args = (reason,)
            elif isinstance(exc.args[0], str):
                x = list(exc.args)
                x[0] += _prefix_reason(x[0])
                exc.args = tuple(x)
    # Add other cases as they arise
    # Otherwise, leave exception unmodified


def caller(ignore_modules=None, exclude_first=True):
    """Which file:line:func is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found. If `ignore_modules` is
    defined, will ignore those modules as well.

    Note: may return __main__ module.

    Will raise exception if calling from __main__

    Args:
        ignore_modules (list): other modules (objects) to exclude [None]
        exclude_first (bool): skip first module found [True]

    Returns:
        PKDict: keys: filename, lineno, name, module
    """
    frame = None
    try:
        exclude = [inspect.getmodule(caller)]
        if ignore_modules:
            exclude.extend(ignore_modules)
        exclude_orig_len = len(exclude)
        # Ugly code, because don't want to bind "frame"
        # in a call.
        frame = inspect.currentframe().f_back
        while True:
            m = inspect.getmodule(frame)
            # getmodule doesn't always work for some reason
            if not m:
                m = sys.modules[frame.f_globals["__name__"]]
            if m not in exclude:
                if len(exclude) > exclude_orig_len or not exclude_first:
                    return Call(frame)
                # Have to go back two exclusions (this module and our caller)
                exclude.append(m)
            frame = frame.f_back
        # Will raise exception if calling from __main__
    finally:
        # If an exception is thrown, the stack
        # hangs around forever. That's what the del frame
        # is for.
        if frame:
            del frame


def caller_func_name():
    """Name of function one frame back

    Useful for inter-module dispatch and errors.

    Returns:
        str: function name
    """
    return inspect.currentframe().f_back.f_back.f_code.co_name


def caller_module(exclude_first=True):
    """Which module is calling the caller of this function.

    Will not return the same module as the calling module, that is,
    will iterate until a new module is found. If exclude_first == True
    it will also exclude the first module found that is not the calling
    module.

    Note: may return __main__ module.

    Will raise exception if calling from __main__

    Args:
        exclude_first (bool): skip first module found [True]

    Returns:
        module: module which is calling module
    """
    return caller(exclude_first=exclude_first)._module


def is_caller_main():
    """Is the caller's calling module __main__?

    Returns:
        bool: True if calling module was called by __main__.
    """
    return caller_module().__name__ == "__main__"


def is_valid_identifier(string):
    """Is this a valid Python identifier?

    Args:
        string (str): what to validate
    Returns:
        bool: True if is valid python ident.
    """
    return bool(_VALID_IDENTIFIER_RE.search(string))


def module_basename(obj):
    """Parse the last part of a module name

    For example, module_basename(pkinspect) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    return module_name_split(obj).pop()


def module_name_join(names):
    """Joins names with '.'

    Args:
        names (iterable): list of strings to join

    Returns:
        str: module name
    """
    return ".".join(names)


def module_name_split(obj):
    """Splits obj's module name on '.'

    Args:
        obj (object): any python object

    Returns:
        str: base part of the module name
    """
    n = inspect.getmodule(obj).__name__
    return n.split(".")


def module_functions(func_prefix, module=None):
    """Get all module level functions starting with func_prefix

    Args:
        func_prefix (str): the prefix of function names to get
        module (object): a module to get functions from (calling module if None)

    Returns:
        PKDict: dict of function name mapped to the function object
    """
    r = PKDict()
    for n, o in inspect.getmembers(module or caller_module(exclude_first=False)):
        if n.startswith(func_prefix) and inspect.isfunction(o):
            r[n] = o
    return r


def package_module_names(name_or_module):
    """List of modules of package `name_or_module`

    Args:
        name_or_module (object): absolute name of package, e.g. pykern.pkcli, or module object
    Returns:
        list: sorted, relative module names, e.g. [ci, fmt, github, ...]
    """
    p = (
        name_or_module
        if inspect.ismodule(name_or_module)
        else importlib.import_module(name_or_module)
    )
    return sorted(
        (
            m.name
            for m in pkgutil.iter_modules([os.path.dirname(p.__file__)])
            if not m.ispkg
        ),
    )


def root_package(obj):
    """Parse the root package in which `obj` is defined.

    For example, root_package(module_basename) is 'pykern'.

    Args:
        obj (object): any python object

    Returns:
        str: root package for the object
    """
    return module_name_split(obj).pop(0)


def submodule_name(obj):
    """Remove the root package in which `obj` is defined.

    For example, root_package(module_basename) is 'pkinspect'.

    Args:
        obj (object): any python object

    Returns:
        str: submodule for the object
    """
    x = module_name_split(obj)
    x.pop(0)
    return module_name_join(x)


def this_module():
    """Module object for caller

    Returns:
        module: module object
    """
    return caller(exclude_first=False)._module

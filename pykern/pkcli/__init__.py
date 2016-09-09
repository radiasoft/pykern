# -*- coding: utf-8 -*-
u"""Invoke commands from command line interpreter modules.

Any module in ``<root_pkg>.pkcli`` will be found by this module. The
public functions of the module will be executed when called from the
command line. This module is invoked by :mod:`pykern.pykern_console`.
Every project must have its own invocation module.

The basic form is: <project> <simple-module> <function>. <simple-module>
is the module without `<root_pkg>.pkcli`.  <function> is any function
that begins with a letter and contains word characters (\w).

If the module only has one public function named default_command,
the form is: <project> <simple-module>.

The purpose of this module is to simplify command-line modules. There is
no boilerplate. You just create a module with public functions
in a particular package location (e.g. `pykern.pkcli`).
This module does the rest.

`pykern.pkcli.pkexample` is a working example.

:copyright: Copyright (c) 2015-2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
import argh
import argparse
import importlib
import inspect
import os.path
import pkgutil
import re
import sys

# Avoid pykern imports so avoid dependency issues for pkconfig
from pykern import pkconfig

#: Sub-package to find command line interpreter (cli) modules will be found
CLI_PKG = ['pkcli', 'pykern_cli']

#: If a module only has one command named this, then execute directly.
DEFAULT_COMMAND = 'default_command'

#: Test for first arg to see if user wants help
_HELP_RE = re.compile(r'^-(-?help|h)$', flags=re.IGNORECASE)


def command_error(fmt, *args, **kwargs):
    """Raise CommandError with msg

    Args:
        fmt (str): how to represent arguments

    Raises:
        CommandError: always
    """
    raise argh.CommandError(fmt.format(*args, **kwargs))


def main(root_pkg, argv=None):
    """Invokes module functions in :mod:`pykern.pykern_cli`

    Looks in ``<root_pkg>.pykern_cli`` for the ``argv[1]`` module. It then
    invokes the ``argv[2]`` method of that module.

    Args:
        root_pkg (str): top level package name
        argv (list of str): Defaults to `sys.argv`. Only used for testing.

    Returns:
        int: 0 if ok. 1 if error (missing command, etc.)
    """
    pkconfig.append_load_path(root_pkg)
    if not argv:
        argv = list(sys.argv)
    prog = os.path.basename(argv.pop(0))
    if _is_help(argv):
        return _list_all(root_pkg, prog)
    module_name = argv.pop(0)
    cli = _module(root_pkg, module_name)
    if not cli:
        return 1
    prog = prog + ' ' + module_name
    parser = argparse.ArgumentParser(
        prog=prog, formatter_class=argh.PARSER_FORMATTER)
    cmds = _commands(cli)
    dc = _default_command(cmds, argv)
    if dc:
        argh.set_default_command(parser, dc)
    else:
        argh.add_commands(parser, cmds)
        if len(argv) < 1:
            # Python 3: parser doesn't exit if not enough commands
            parser.error('too few arguments')
        if argv[0][0] != '-':
            argv[0] = argv[0].replace('_', '-')
    argh.dispatch(parser, argv=argv)
    return 0


def _commands(cli):
    """Extracts all public functions from `cli`

    Args:
        cli (module): where commands are executed from

    Returns:
        list of function: public functions sorted alphabetically
    """
    res = []
    for n, t in inspect.getmembers(cli):
        if _is_command(t, cli):
            res.append(t)
    sorted(res, key=lambda f: f.__name__.lower())
    return res


def _default_command(cmds, argv):
    """Evaluate the default command, handling ``**kwargs`` case.

    `argparse` and `argh` do not understand ``**kwargs``, i.e. pass through command.
    There's a case (`pykern.pkcli.pytest`) that requires pass through so we wrap
    the command and clear `argv` in the case of ``default_command(*args, **kwargs)``.

    Args:
        cmds (list): List of commands
        argv (list): arguments (may be edited)

    Returns:
        function: default command or None
    """
    if len(cmds) != 1 or cmds[0].__name__ != DEFAULT_COMMAND:
        return None
    dc = cmds[0]
    spec = inspect.getargspec(dc)
    if not (spec.varargs and spec.keywords):
        return dc
    save_argv = argv[:]
    def _wrap_default_command():
        return dc(*save_argv)
    del argv[:]
    return _wrap_default_command


def _import(root_pkg, name=None):
    """Dynamically imports ``root_pkg.CLI_PKG[.name]``.

    Args:
        root_pkg (str): top level package
        name (str): cli module

    Returns:
        module: imported module

    Raises:
        ImportError: if module could not be loaded
    """
    def _imp(path_list):
        p = '.'.join(path_list).replace('-', '_')
        return importlib.import_module(p)


    #TODO(robnagler) remove once all clients support pkcli directory
    path = None
    first_e = None
    m = None
    for p in CLI_PKG:
        path = [root_pkg, p]
        try:
            m = _imp(path)
            break
        except ImportError as e:
            # Assumes package (foo.pkcli) has an empty __init__.py so that
            # the import should always succeed.
            if not first_e:
                first_e = e
    if not path:
        raise first_e
    if not name:
        return m
    return _imp(path + [name])


def _is_command(obj, cli):
    """Is this a valid command function?

    Args:
        obj (object): candidate
        cli (module): module to which function should belong

    Returns:
        bool: True if obj is a valid command
    """
    if not inspect.isfunction(obj) or obj.__name__.startswith('_'):
        return False
    return hasattr(obj, '__module__') and obj.__module__ == cli.__name__;


def _is_help(argv):
    """Does the user want help?

    Args:
        argv (list): list of args

    Returns:
        bool: True if no args or --help
    """
    if len(argv) == 0:
        return True
    return _HELP_RE.search(argv[0])


def _list_all(root_pkg, prog):
    """Prints a list of importable modules and exits.

    Searches ``<root_pkg>.pykern_cli` for submodules, and prints their names.

    Args:
        root_pkg (str): top level package
        prog (str): argv[0], name of program invoked

    Returns:
        int: 0 if ok. 1 if error.

    """
    res = []
    pykern_cli = _import(root_pkg)
    path = os.path.dirname(pykern_cli.__file__)
    for _, n, ispkg in pkgutil.iter_modules([path]):
        if not ispkg:
            res.append(n.replace('_', '-'))
    sorted(res, key=str.lower)
    res = '\n'.join(res)
    sys.stderr.write(
        'usage: {} module command [args...]\nModules:\n{}\n'.format(prog, res),
    )
    return 1


def _module(root_pkg, name):
    """Imports the module, catching `ImportError`

    Args:
        root_pkg (str): top level package
        name(str): unqualified name of the module to be imported

    Returns:
        module: imported module
    """
    try:
        return _import(root_pkg, name)
    except Exception as e:
        sys.stderr.write(str(e) + "\n")
    return None

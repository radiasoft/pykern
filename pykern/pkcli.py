# -*- coding: utf-8 -*-
u"""Invoke commands from command line interpreter modules.

Any module in ``<root_pkg>.pykern_cli`` will be found by this module. The
public functions of the module will be executed when called from the
command line. This module is invoked by :mod:`pykern.pykern_console`.
Every project must have its own invocation module.

The basic form is: <project> <simple-module> <function>. <simple-module>
is the module without `<root_pkg>.pykern_cli`.  <function> is any function
that begins with a letter and contains word characters (\w).

If the module only has one public function named default_command,
the form is: <project> <simple-module>.

The purpose of this module is to simplify command-line modules. There is
no boilerplate. You just create a module with public functions
in a particular package location (e.g. `pykern.pykern_cli`).
This module does the rest.

Example:

    If you are in project ``foobar``, you would create
    a ``foobar_console.py``, which would contain::

        import sys

        import pykern.cli


        def main():
            return pykern.cli.main('foobar')


        if  __name__ == '__main__':
            sys.exit(main())

    To invoke :func:`foobar.pykern_cli.projex.snafu` command,
    you run the following from the command line::

        foobar projex snafu

    This module uses :mod:`argh` so cli modules can specify arguments and
    such as follows::

        @argh.arg('greet', default='hello world', nargs='+', help='salutation')
        def func(greet):

    If you are using Python 3, you can say::

        def func(greet : 'salutation')

:copyright: Copyright (c) 2015 Bivio Software, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

import argparse
import importlib
import inspect
import os.path
import pkgutil
import re
import sys

import argh

#: Sub-package to find command line interpreter (cli) modules will be found
CLI_PKG = 'pykern_cli'

#: If a module only has one command named this, then execute directly.
DEFAULT_COMMAND = 'default_command'


#: Test for first arg wanting help
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
    has_default_command = len(cmds) == 1 and cmds[0].__name__ == DEFAULT_COMMAND
    if has_default_command:
        argh.set_default_command(parser, cmds[0])
    else:
        argh.add_commands(parser, cmds)
    # Python 3: parser doesn't exit if not enough commands
    if len(argv) < 1 and not has_default_command:
        parser.error('too few arguments')
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
    p = [root_pkg, CLI_PKG]
    if name:
        p.append(name)
    return importlib.import_module('.'.join(p))


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
            res.append(n)
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

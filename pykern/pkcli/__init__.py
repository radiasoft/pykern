"""Invoke commands from command line interpreter modules.

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

:copyright: Copyright (c) 2015-2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

import argh
import argh.assembling
import argh.constants
import argparse
import importlib
import inspect
import itertools
import os
import os.path
import pkgutil
import re
import sys
import types

# Avoid pykern imports so avoid dependency issues for pkconfig
from pykern import pkconfig
from pykern import pkconst
from pykern import pkinspect

#: Sub-package to find command line interpreter (cli) modules will be found
CLI_PKG = ["pkcli"]

#: If a module only has one command named this, then execute directly.
DEFAULT_COMMAND = "default_command"

#: Test for first arg to see if user wants help
_HELP_RE = re.compile(r"^-(-?help|h)$", flags=re.IGNORECASE)

#: Used by `_fix_sys_path`
_fix_sys_path_done = False


class CommandError(Exception):
    """argh.CommandError is caught by argh, and does not cause an exit

    This CommandError causes an exit(1).
    """

    pass


def command_error(fmt, *args, **kwargs):
    """Raise CommandError with msg

    Args:
        fmt (str): how to represent arguments

    Raises:
        CommandError: always
    """
    raise CommandError(fmt.format(*args, **kwargs))


def command_info(fmt, *args, **kwargs):
    """Write message to stderr without raising

    Args:
        fmt (str): how to represent arguments
    """
    sys.stderr.write(fmt.format(*args, **kwargs))


class CustomFormatter(argh.constants.CustomFormatter):
    def _expand_help(self, action):
        return super()._expand_help(action).split("\n")[0]


class CustomParser(argh.ArghParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.program = kwargs.copy()
        self.options = []

    def format_help(self):
        f = argh.PARSER_FORMATTER(prog=self.prog)
        if not self.description:
            f = CustomFormatter(prog=self.prog)
        f.add_usage(self.usage, self._actions, self._mutually_exclusive_groups)
        f.add_text(self.description)
        for a in self._action_groups:
            f.start_section(a.title)
            f.add_text(a.description)
            f.add_arguments(a._group_actions)
            f.end_section()
        f.add_text(self.epilog)
        if not self.description:
            return f.format_help().replace("positional arguments", "commands")
        return f.format_help()

    def print_help(self):
        pkconst.builtin_print(self.format_help())


def main(root_pkg, argv=None):
    """Invokes module functions in :mod:`pykern.pkcli`

    Looks in ``<root_pkg>.pkcli`` for the ``argv[1]`` module. It then
    invokes the ``argv[2]`` method of that module.

    Args:
        root_pkg (str): top level package name
        argv (list of str): Defaults to `sys.argv`. Only used for testing.

    Returns:
        int: 0 if ok. 1 if error (missing command, etc.)
    """
    _fix_sys_path()
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
    if c := getattr(cli, "Commands", None):
        cli = c()
    prog = prog + " " + module_name
    parser = CustomParser(prog)
    cmds = _commands(cli)
    dc = _default_command(cmds, argv)
    if dc:
        argh.set_default_command(
            parser,
            dc,
            **_argh_name_mapping_policy(),
        )
    else:
        argh.add_commands(
            parser,
            cmds,
            **_argh_name_mapping_policy(),
        )
        if len(argv) < 1:
            # Python 3: parser doesn't exit if not enough commands
            parser.error("too few arguments")
        if argv[0][0] != "-":
            argv[0] = _module_to_cmd(argv[0])
    try:
        res = argh.dispatch(parser, argv=argv)
    except CommandError as e:
        sys.stderr.write("error: {}\n".format(e))
        return 1
    return 0


def _argh_name_mapping_policy():
    """Return name_mapping_policy based on feature test of NameMappingPolicy.

    In v0.30.0 argh changed the policy for mapping function args to
    CLI args. For versions 0.30.0 and above this sets the policy to
    BY_NAME_IF_HAS_DEFAULT which most closely matches the behavior
    prior to v0.30.0.
    """
    p = getattr(argh.assembling, "NameMappingPolicy", None)
    if not p:
        # Prior to v0.30.0 there was no NameMappingPolicy policy so no
        # need to set.
        return {}
    return {"name_mapping_policy": p.BY_NAME_IF_HAS_DEFAULT}


def _commands(cli):
    """Extracts all public functions or methods from `cli`

    Args:
        cli (object): where commands are executed from

    Returns:
        list: commands sorted alphabetically
    """

    def _functions():
        return _iter(
            lambda t: inspect.isfunction(t)
            and hasattr(t, "__module__")
            and t.__module__ == cli.__name__
        )

    def _iter(predicate):
        for n, t in inspect.getmembers(cli, predicate=predicate):
            if not n.startswith("_"):
                yield (t)

    def _methods():
        x = frozenset(_super_methods())
        return _iter(
            lambda t: inspect.ismethod(t)
            and t.__name__ not in x
            and t.__name__ in dir(cli)
        )

    def _super_methods():
        return itertools.chain(*(dir(b) for b in cli.__class__.__bases__))

    return sorted(
        _functions() if isinstance(cli, types.ModuleType) else _methods(),
        key=lambda f: f.__name__.lower(),
    )


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
    spec = inspect.getfullargspec(dc)
    if not (spec.varargs and spec.kwonlyargs):
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
        return importlib.import_module(_module_name(path_list))

    # TODO(robnagler) remove once all clients support pkcli directory
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

    Searches ``<root_pkg>.pkcli` for submodules, and prints their names.

    Args:
        root_pkg (str): top level package
        prog (str): argv[0], name of program invoked

    Returns:
        int: 0 if ok. 1 if error.

    """
    res = "\n".join(
        sorted(
            pkinspect.package_module_names(_import(root_pkg)),
            key=str.lower,
        ),
    )
    sys.stderr.write(f"usage: {prog} module command [args...]\nModules:\n{res}\n")
    return 1


def _module(root_pkg, name):
    """Imports the module, catching `ImportError`

    Args:
        root_pkg (str): top level package
        name(str): unqualified name of the module to be imported

    Returns:
        module: imported module
    """

    def _match_exc(e):
        return re.search(
            " {}$|{}".format(
                # py2
                _module_from_cmd(name),
                # py3
                _module_name((root_pkg, name)),
            ),
            str(e),
        )

    try:
        return _import(root_pkg, name)
    except Exception as e:
        if (
            isinstance(e, ImportError)
            and _match_exc(e)
            or isinstance(e, (argh.CommandError, CommandError))
        ):
            sys.stderr.write(str(e) + "\n")
        else:
            raise
    return None


def _module_from_cmd(cmd):
    return cmd.replace("-", "_")


def _module_name(path_list):
    return _module_from_cmd(".".join(path_list))


def _module_to_cmd(module):
    return module.replace("_", "-")


def _fix_sys_path():
    """Remove the script directory from `sys.path`

    The script's directory is added to sys.path by the interpreter. In
    Python 3.11, this will change with the ``-P`` flag.
    """
    global _fix_sys_path_done

    if _fix_sys_path_done:
        return
    _fix_sys_path_done = True
    if not (sys.argv and sys.path):
        # Not enough information
        return
    d = os.path.dirname(os.path.realpath(sys.argv[0]))
    if sys.path[0] == d:
        sys.path.pop(0)

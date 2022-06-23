# -*- coding: utf-8 -*-
"""Demonstrate how to write reusable command line tools.

A `pykern.pkcli` module is designed to be used from any context
any other piece of code. Since we use `argh`, it makes it easy
to dispatch with a bit of glue so that all you have to do is write
a function.

Documentation should be provided as a normal docstring for the function.
See `echo`.

You should set up your project directory with `pykern.pkcli.projex`,
which will give you a shell command that gets automatically
installed. Each project has one such command. For example,
`pykern.pykern_console` is the module that invokes all `pykern`
pkcli functions.

To invoke `echo`, use the shell command::

    $ pykern pkexample echo something
    howdy: something

The output of the function is printed on stdout so if you don't
have to print messages, and the function can be used in other
contexts where stdout is not useful (e.g. returned to a brower).

If you invoke this module without arguments, you get a list of
functions you can call:

    $ pykern pkexample
    usage: pykern pkexample [-h] {echo,primes} ...
    pykern pkexample: error: too few arguments

This list only includes "public" functions (not beginning with
an underscore).

In your project, you'll have your own function, for example,
you can start Sirepo with::

    $ sirepo service http
     * Running on http://0.0.0.0:8000/
     * Restarting with reloader

The module `sirepo.sirepo_console` is automatically installed
as a shell command by ``setup.py``, and `pykern.pkcli` searches
for modules to invoke in the package `sirepo.pkcli`. In fact,
you can list out all modules by invoking ``sirepo`` without
any arguments::

    $ sirepo
    usage: sirepo module command [args...]
    Modules:
    celery
    elegant
    service
    srw
    warp

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcli
import itertools


def echo(suffix, prefix="howdy: "):
    """Concatenate prefix and suffix

    Args:
        to_echo (str): what to print and must be at least five chars
        prefix (str): what to put in front of `to_echo` ["howdy: "]

    Returns:
        str: prefix + suffix
    """
    if len(suffix) < 5:
        # We raise argument and other errors with command_error, which
        # raises `pkcli.CommandError` in a nice way. We use Unix-style
        # error messages, that is, problematic object followed by colon
        # followed by an error message and any other details.
        pkcli.command_error("{}: suffix is too short (< 5 chars)", suffix)
    # Instead of printing messages in the simple case, we just
    # return the value. This way the function can be used in
    # other contexts. argh prints the return of the function to stdout.
    return prefix + suffix

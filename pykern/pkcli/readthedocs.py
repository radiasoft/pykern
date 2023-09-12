# -*- coding: utf-8 -*-
"""generate files needed for readthedocs

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
import copy
import datetime
import subprocess

def sphinx_apidoc():
    """Call `sphinx-apidoc` with appropriately configured ``conf.py``."""

    def _read(filename):
        """Open and read filename

        Args:
            filename (str): what to read

        Returns:
            str: contents of filename
        """
        with open(filename, "r") as f:
            return f.read()

    def _write(filename, content):
        """Writes a file"""
        with open(filename, "w") as f:
            f.write(content)

    #name = kwargs["name"]
    name = "pykern"
    p = _packages("pykern")

    values = {
        "empty_braces": "{}",
        "name": name,
        "packages": p,
        "year": datetime.datetime.now().year,
    }

    from pykern import pkresource

    data = _read(pkresource.filename("docs-conf.py.format"))
    _write("docs/conf.py", data.format(**values))
    subprocess.check_call(
        [
            "sphinx-apidoc",
            "-f",
            "-o",
            "docs",
        ]
        + p,
    )


def _packages(name):
    """Find all packages by looking for ``__init__.py`` files.

    Mostly borrowed from https://bitbucket.org/django/django/src/tip/setup.py

    Args:
        name (str): name of the package (directory)

    Returns:
        list: packages names
    """
    import os

    def _fullsplit(path, result=None):
        """
        Split a pathname into components (the opposite of os.path.join) in a
        platform-neutral way.

        """
        if result is None:
            result = []
        head, tail = os.path.split(path)
        if head == "":
            return [tail] + result
        if head == path:
            return result
        return _fullsplit(head, [tail] + result)

    res = []
    for (
        dirpath,
        _,
        filenames,
    ) in os.walk(name):
        if "__init__.py" in filenames:
            res.append(str(".".join(_fullsplit(dirpath))))
    return res


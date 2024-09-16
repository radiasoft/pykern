"""Initialize Python project directories

:copyright: Copyright (c) 2015 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcli
from pykern import pkio
from pykern import pkjinja
from pykern import pkresource
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdp
import copy
import datetime
import os
import py.path
import re
import subprocess

#: Default values
DEFAULTS = {
    "year": datetime.datetime.now().year,
    "license": "apache2",
    "copyright_license_rst": """:copyright: Copyright (c) {year} {author}.  All Rights Reserved.
:license: {license}""",
}


#: Licenses
LICENSES = {
    "agpl3": (
        "https://www.gnu.org/licenses/agpl-3.0.txt",
        "License :: OSI Approved :: GNU Affero General Public License v3",
    ),
    "apache2": (
        "https://www.apache.org/licenses/LICENSE-2.0.html",
        "License :: OSI Approved :: Apache Software License",
    ),
    "gpl2": (
        "https://www.gnu.org/licenses/gpl-2.0.txt",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ),
    "gpl3": (
        "https://www.gnu.org/licenses/gpl-3.0.txt",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ),
    "lgpl2": (
        "https://www.gnu.org/licenses/lgpl-2.0.txt",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
    ),
    "lgpl3": (
        "https://www.gnu.org/licenses/lgpl-3.0.txt",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    ),
    "mit": (
        "https://opensource.org/licenses/MIT",
        "License :: OSI Approved :: MIT License",
    ),
    "proprietary": (
        "PROPRIETARY AND CONFIDENTIAL. See LICENSE file for details.",
        "License :: Other/Proprietary License",
    ),
}

_UPGRADE_PKSETUP_KEYS = frozenset(
    (
        "author",
        "author_email",
        "classifiers",
        "description",
        "license",
        "name",
        "url",
    )
)


_IGNORE_CLASSIFIERS = frozenset(
    [
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python",
        "Topic :: Utilities",
    ]
    + [c[1] for c in LICENSES.values()],
)


_RS_GIT_URL = "https://git.radiasoft.org/"


def init_rs_tree(description):
    """Initialize defaults for RadiaSoft project tree and call `init_tree`

    `description` is passed verbatim. Other args passed to `init_tree`:

    name
       Base name of the current directory
    author
       "RadiaSoft LLC"
    author_email
       "pip@radiasoft.net"
    license
       "apache2"
    url
       "https://git.radiasoft.org/{name}"

    Args:
        description (str): one-line summary of project
    """
    name = py.path.local().basename
    init_tree(
        name,
        "RadiaSoft LLC",
        "pip@radiasoft.net",
        description,
        "apache2",
        _RS_GIT_URL + name,
    )


def init_tree(name, author, author_email, description, license, url, overwrite=False):
    """Setup a project tree with: docs, tests, etc., and checkin to git.

    Creates: pyproject.toml, index.rst, project dir, <name>_console.py, etc.
    Overwrites files if they exist without checking.

    Args:
        name (str): short name of the project, e.g. ``pykern``.
        author (str): copyright holder, e.g. ``RadiaSoft LLC``
        author_email (str): how to reach author, e.g. ``pip@pykern.org``
        description (str): one-line summary of project
        license (str): name of license, e.g. apache2, mit, and proprietary.
        url (str): website for project, e.g. https://pykern.org
        overwrite (bool): overwrite existing files [False]
    """
    assert os.path.isdir(".git"), "Must be run from the root directory of the repo"
    assert overwrite or not os.path.isdir(
        name
    ), "{}: already exists, only works on fresh repos".format(name)
    assert (
        name == py.path.local().basename
    ), "{}: name must be the name of the current directory".format(name)
    license = license.lower()
    base = pkresource.filename("projex")
    values = copy.deepcopy(DEFAULTS)
    values.update(
        name=name,
        author=author,
        description=description,
        author_email=author_email,
        url=url,
        license=_license(license, 0),
        classifier_license=_license(license, 1),
    )
    values["copyright_license_rst"] = values["copyright_license_rst"].format(**values)
    suffix_re = r"\.jinja$"
    for src in pkio.walk_tree(base, file_re=suffix_re):
        dst = py.path.local(src).relto(str(base))
        dst = dst.replace("projex", name).replace("dot-", ".")
        dst = re.sub(suffix_re, "", dst)
        pkio.mkdir_parent_only(dst)
        _render(src, values, output=dst)
    src = py.path.local(pkresource.filename("projex-licenses"))
    src = src.join(license + ".jinja")
    _render(src, values, output="LICENSE")


def upgrade_tree():
    """Upgrade from setup.py to pyproject.toml

    Replaces all generated files.
    """

    def _classifiers(old_list):
        rv = list(filter(lambda c: c not in _IGNORE_CLASSIFIERS, old_list))
        if rv:
            return ["classifiers in pyproject.toml trimmed, maybe add:"] + rv
        return []

    def _delete_unknown_keys(kwargs):
        x = set(kwargs.keys()) - _UPGRADE_PKSETUP_KEYS
        if not x:
            return []
        return ["Update these keys in pyproject.toml:"] + [
            f"    {k}={kwargs.pkdel(k)}" for k in sorted(x)
        ]

    def _dependencies(install_requires):
        o = pkio.read_text("pyproject.toml")
        n = o.replace(
            '    "pykern"', ",\n".join([f'    "{k}"' for k in install_requires])
        )
        pkio.write_text("pyproject.toml", n)

    def _license_key(url):
        url = url.replace("http:", "https:")
        for k, v in LICENSES.items():
            if v[0] == url:
                return k
        pkcli.command_error("unknown license url={} in setup.py", url)

    def _readme(old_txt, kwargs):
        if old_txt.startswith(
            f"""### {kwargs.name}

{kwargs.description}

Learn more at http"""
        ):
            return []
        pkio.write_text("README.md", old_txt)
        rv = [
            "README.md left intact; update documentation url to:",
            f"    https://{kwargs.name}.readthedocs.io",
        ]
        if kwargs.url.startswith(_RS_GIT_URL):
            rv += [
                "Update project url to:",
                f"    {kwargs.url}",
            ]
        return rv

    def _url(old_url, name):
        if old_url == f"https://github.com/radiasoft/{name}":
            return _RS_GIT_URL + name
        return old_url

    rv = []
    s = _pksetup_kwargs()
    o = PKDict({k: s.pkdel(k) for k in ("classifiers", "install_requires")})
    o.readme = pkio.read_text("README.md")
    rv += _classifiers(o.classifiers)
    rv += _delete_unknown_keys(s)
    s.license = _license_key(s.license)
    s.url = _url(s.url, s.name)
    s.overwrite = True
    init_tree(**s)
    _dependencies(o.install_requires)
    rv += _readme(o.readme, s)
    pkio.unchecked_remove("setup.py", f"{s.name}/base_pkconfig.py")
    return "\n".join(rv + ["Run git diff and then git commit changes"])


def _license(name, which):
    """Returns matching license or command_error"""
    try:
        return LICENSES[name][which]
    except KeyError:
        pkcli.command_error(
            "{}: unknown license name. Valid licenses: {}",
            name,
            " ".join(sorted(LICENSES.values())),
        )


def _pksetup_kwargs():
    """Extra kwargs passed to to setup in setup.py for the old project

    Monkey patches `pksetup.setup` to capture its kwargs.

    Returns:
        PKDict: kwargs passed to setup

    """
    from pykern import pksetup, pkrunpy

    rv = None

    def _save(**kwargs):
        nonlocal rv
        rv = PKDict(kwargs)

    p = getattr(pksetup, "setup")
    try:
        setattr(pksetup, "setup", _save)
        pkrunpy.run_path_as_module("setup.py")
        return rv
    finally:
        setattr(pksetup, "setup", p)


def _render(*args, **kwargs):
    """Renders the template and adds to git"""
    pkjinja.render_file(*args, **kwargs)
    subprocess.check_call(["git", "add", kwargs["output"]])

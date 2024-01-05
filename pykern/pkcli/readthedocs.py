# -*- coding: utf-8 -*-
"""generate files needed for readthedocs

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

def run():
    _sphinx_conf(
        author="RadiaSoft LLC",
        author_email="pip@pykern.org",
        description="Python application support",
        name="pykern",
    )


def _sphinx_conf(**kwargs):
    """Generate ``conf.py`` for use with `sphinx-apidoc`."""

    import datetime
    from pykern import pkresource
    from pykern import pksetup

    values = {
        "empty_braces": "{}",
        "packages": pksetup.packages(kwargs["name"]),
        "year": datetime.datetime.now().year,
    }
    values.update(kwargs)
    values["version"], _ = pksetup.version(values)

    with open(pkresource.filename("docs-conf.py.format"), "r") as f:
        with open("docs/conf.py", "w") as c:
            c.write(f.read().format(**values))


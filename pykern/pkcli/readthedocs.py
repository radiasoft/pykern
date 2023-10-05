# -*- coding: utf-8 -*-
"""generate files needed for readthedocs

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

def run():
    _sphinx_conf(
        author="nobody",
        description="nothing",
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

    with open("docs/conf.py", "w") as f:
        f.write(
            pksetup.read(pkresource.filename("docs-conf.py.format")).format(**values)
        )


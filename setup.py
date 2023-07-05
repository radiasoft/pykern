# -*- coding: utf-8 -*-
"""Install PyKern

:copyright: Copyright (c) 2015-2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pksetup import setup


def _requires():
    r = [
        "argh>=0.26",
        "black~=22.12",
        "future>=0.14",
        "github3.py>=1.1",
        # for virtualenv
        "importlib-metadata>=0.12",
        "jinja2>=2.7",
        "openpyxl>=3.0.9",
        "pandas>=1.3.2",
        "psutil>=5.0",
        "py-cpuinfo>=0.2",
        "py>=1.4",
        "pytest>=2.7",
        "pytz>=2015.4",
        "ruamel.yaml>=0.16.0",
        "requests>=2.18",
        # setuptools breaks almost every release so limiting is safer than not
        "setuptools>=62,<63",
        "six>=1.9",
        "Sphinx>=1.3.5",
        "twine>=1.9",
        "tox>=1.9",
        "packaging>=21.0",
        "path.py>=7.7.1",
        "python-dateutil>=2.4.2",
        "XlsxWriter>=3.0.3",
        # for tox
        "pluggy>=0.12.0",
    ]
    v = "urllib3"
    # Adapted from urllib3
    # https://github.com/urllib3/urllib3/blob/2ac40569acb464074bdc3f308124d781d6aa0860/src/urllib3/__init__.py#L28
    try:
        import ssl
    except ImportError:
        pass
    else:

        def _ssl_is_not_openssl():
            """python ssl is not compiled with OpenSSL (ex LibreSSL on MacOS).

            https://github.com/urllib3/urllib3/issues/3020
            """
            return not ssl.OPENSSL_VERSION.startswith("OpenSSL ")

        if _ssl_is_not_openssl() or ssl.OPENSSL_VERSION_INFO < (1, 1, 1):
            v += "==1.26.16"
    r.append(v)
    return r


setup(
    name="pykern",
    description="Python application support",
    author="RadiaSoft LLC",
    author_email="pip@pykern.org",
    install_requires=_requires(),
    license="http://www.apache.org/licenses/LICENSE-2.0.html",
    url="http://pykern.org",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Utilities",
    ],
)

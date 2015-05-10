#!/bin/bash
sphinx-apidoc -f -o docs/source pykern
cd docs
make html

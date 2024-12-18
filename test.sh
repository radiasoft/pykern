#!/bin/bash
#
# Run pkcli.ci in parallel
#
set -euo pipefail

_main() {
    PYKERN_PKCLI_TEST_MAX_PROCS=4 pykern ci run
}

_main "$@"

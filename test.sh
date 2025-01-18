#!/bin/bash
#
# Run pkcli.ci in parallel
#
set -euo pipefail

_main() {
    PYKERN_PKDEBUG_WANT_PID_TIME=1 PYKERN_PKCLI_TEST_MAX_PROCS=4 pykern ci run
}

_main "$@"

#!/bin/bash
#
# Check for debug statements and run all tests
#
set -euo pipefail

test_err() {
    test_msg "$@"
    return 1
}

test_main() {
    local pyfiles=( $(find pykern -name \*.py | egrep -v 'pkdebug\.py' | sort) )
    test_no_prints '\s(pkdp)\(' "${pyfiles[@]}"
    pykern test
}

test_msg() {
    echo "$@" 1>&2
}

test_no_prints() {
    local pat=$1
    shift
    local f=( $@ )
    local r=$(egrep -l "$pat" "${f[@]}")
    if [[ $r ]]; then
        test_err "$pat found in: $r"
    fi
}

test_main "$@"

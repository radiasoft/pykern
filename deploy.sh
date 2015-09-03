#!/bin/sh
if [[ $TRAVIS_JOB_NUMBER =~ \.1$ ]]; then
    echo deploying $(date)
fi

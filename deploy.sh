#!/bin/sh
echo 'BEGIN ####################################'
ls -altr
env 2>&1 | grep -v PYKERN
echo 'END ####################################'

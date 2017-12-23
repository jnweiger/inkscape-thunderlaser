#!/bin/sh
#
# run tests on the inkscape-thunderlaser extension.


dir=$(dirname $0)
svg=$1
test -z "$svg" && svg="$dir/Zeichnung.svg"
test -n "$2" && ids="--id=$2"   # --id=rect4485

$dir/test_simple.sh $svg
$dir/test_styles.sh

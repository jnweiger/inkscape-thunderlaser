#!/bin/sh
#
# run the inkscape-thunderlaser extension standalone.


dir=$(dirname $0)
svg=$1
test -z "$svg" && svg="$dir/Zeichnung.svg"
test -n "$2" && ids="--id=$2"   # --id=rect4485

export PYTHONPATH=/usr/share/inkscape/extensions/
set -x
python $dir/../thunderlaser.py $ids --cut_color=any --cut_group=cut_wood --cut_wood="30,7,18" --smoothness=0.2 --freq1=20 --maxwidth=900 --maxheight=600 --bbox_only=false --dummy=true $svg
python $dir/../thunderlaser.py $ids c-cut_color=any --cut_group=cut_wood --cut_wood="30,7,18" --smoothness=0.2 --freq1=20 --maxwidth=900 --maxheight=600 --bbox_only=false --dummy=false --device=/tmp/thunderlaser.rd $svg

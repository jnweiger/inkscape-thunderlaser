#!/bin/sh
# as simple as that:

echo "Building $1 version $2"
echo "======================"

sed -i -e "s/define ShortName \"inkscape\-.*\"\$/define ShortName \"inkscape-$1\"/" installer.nsi
sed -i -e "s/define AppVersion \"v.*\"\$/define AppVersion \"v$2\"/"                installer.nsi

makensis installer.nsi


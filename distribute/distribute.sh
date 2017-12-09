#!/bin/bash
echo "Determining Version:"
VERSION=$(echo '<xml height="0"/>' | python ../thunderlaser.py --version /dev/stdin)	

test -e /usr/bin/xpath || sudo apt-get install libxml-xpath-perl
#
# grep Version ../*.inx
xpath -q -e '//param[@name="about_version"]/text()' ../thunderlaser.inx
echo "Version should be: \"$VERSION\""

VERSION=$(echo "$VERSION" | sed -e 's/version\s*//i')


name=inkscape-thunderlaser
if [ -d $name ]
then
	echo "Removing leftover files"
	rm -rf $name
fi
echo "Copying contents ..."
mkdir $name
cp ../README.md $name/README
cp ../LICENSE* $name/
cp ../*.py ../*.inx ../Makefile $name/
cp ../src/*.sh ../src/*.rules ../src/*.png  $name/

# remove the devel hint, if any. Obsoleted by make nodevel.
sed -i -e 's@\s*(*devel)*</_name>@</_name>@i' -e 's@\.devel</id>@</id>@i' $name/*.inx

echo "****************************************************************"
echo "The Ubuntu build requires checkinstall and dpkg."
echo ""
echo "Build Ubuntu Version (Y/n)?"
read answer
if [ "$answer" != "n" ]
then
  mkdir -p deb/files
  cp -a $name/* deb/files
  (cd deb && sh ./dist.sh $name $VERSION)
fi


echo "Built packages are in distribute/out :"
ls -la out
echo "Cleaning up..."
rm -rf $name
echo "done."

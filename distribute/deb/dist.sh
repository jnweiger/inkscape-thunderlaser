#! /bin/bash
# Make a debian/ubuntu distribution
# Workaround for broken inkscape extension localization:
# - We have multiple *.inx files, one per language.
# - we have multiple make install* targets, one per language.
# - we build multiple binary *.deb packages, one per language.

name=$1
vers=$2
url=http://github.com/jnweiger/$name
# versioned dependencies need \ escapes to survive checkinstall mangling.
# requires="python-usb\ \(\>=1.0.0\), bash"

## not even ubuntu 16.04 has python-usb 1.0,  we requre any python-usb
## and check at runtime again.
requires="python-usb, bash"

build_deb_package() {
  pkgname=$1
  maketarget=$2
  fakeroot checkinstall --fstrans --reset-uid --type debian \
    --install=no -y --pkgname $pkgname --pkgversion $vers --arch all \
    --pkgrelease=$(date +%Y%m%d)jw --pkglicense LGPL --pkggroup other \
    --pakdir ../$tmp --pkgsource $url \
    --pkgaltsource "http://wiki.fablab-nuernberg.de/w/Nova_35" \
    --maintainer "'Juergen Weigert (juewei@fabmail.org)'" \
    --requires "$requires" make $maketarget \
    -e PREFIX=/usr || { echo "fakeroot checkinstall error "; exit 1; }
}

tmp=../out

[ -d $tmp ] && rm -rf $tmp/*.deb
mkdir -p $tmp
cp *-pak files/
cd files
build_deb_package $name    install
build_deb_package $name-de install_de
build_deb_package inkscape-bodor-de install_bodor_de

for deb in ../$tmp/*.deb; do
  dpkg-deb --info     $deb
  dpkg-deb --contents $deb
done

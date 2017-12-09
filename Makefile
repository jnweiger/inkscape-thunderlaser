# a simple makefile to pull a tar ball.

PREFIX?=/usr
DISTNAME=inkscape-thunderlaser
EXCL=--exclude \*.orig --exclude \*.pyc
ALL=README.md *.png *.sh *.rules *.py *.inx
VERS=$$(echo '<xml height="0"/>' | python ./thunderlaser.py --version /dev/stdin)	

# apt-get -t jessie-backports install python-usb
# vi /etc/group
# lp:x:debian


DEST=$(DESTDIR)$(PREFIX)/share/inkscape/extensions
UDEV=$(DESTDIR)/lib/udev

all: clean build check

build: thunderlaser.py thunderlaser.inx

dist:   build check nodevel
	cd distribute; sh ./distribute.sh

check:
	test/test.sh

thunderlaser.inx:
	sed -e 's/>thunderlaser\-ruida\.py</>thunderlaser.py</g' < src/thunderlaser-ruida.inx > $@
	# remove the ruida.py and inksvg.py dependency as they are inlined.
	sed -e '/\(ruida\|inksvg\)\.py<.dependency/d' -i $@
	# add a development hint, to distinguish from any simultaneously installed released version.
	sed -e 's@</_name>@ (devel)</_name>@' -e 's@</id>@\.devel</id>@' -i $@

nodevel: thunderlaser.inx
	# remove the development hints
	sed -i -e 's@\s*(*devel)*</_name>@</_name>@i' -e 's@\.devel</id>@</id>@i' thunderlaser.inx

thunderlaser.py:
	sed >  $@ -e '/INLINE_BLOCK_START/,$$d' < src/thunderlaser-ruida.py
	sed >> $@ -e '/if __name__ ==/,$$d' < src/inksvg.py
	sed >> $@ -e '/if __name__ ==/,$$d' < src/ruida.py
	sed >> $@ -e '1,/INLINE_BLOCK_END/d' < src/thunderlaser-ruida.py

#install is used by dist.
install: nodevel
	mkdir -p $(DEST)
	# CAUTION: cp -a does not work under fakeroot. Use cp -r instead.
	install -m 755 -t $(DEST) *.py
	install -m 644 -t $(DEST) *.inx
	mkdir -p $(UDEV)/rules.d
	install -m 644 -T thunderlaser-udev.rules $(UDEV)/rules.d/40-thunderlaser-udev.rules
	install -m 644 -t $(UDEV) thunderlaser-icon.png
	install -m 644 -t $(UDEV) thunderlaser-udev-notify.sh


tar_dist_classic: clean nodevel
	name=$(DISTNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
	grep about_version ./thunderlaser.inx
	@echo version should be $(VERS)

tar_dist: nodevel
	python setup.py sdist --format=bztar
	mv dist/*.tar* .
	rm -rf dist

clean:
	rm -f thunderlaser.py thunderlaser.inx
	rm -f *.orig */*.orig
	rm -rf distribute/$(DISTNAME)
	rm -rf distribute/deb/files


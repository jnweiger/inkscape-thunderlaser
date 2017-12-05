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

all: clean build check dist

build: thunderlaser.py thunderlaser.inx

dist:
	cd distribute; echo sh ./distribute.sh

check:
	test/test.sh

thunderlaser.inx:
	sed -e 's/>ruida\-laser\.py</>thunderlaser.py</g' < src/ruida-laser.inx > $@
	sed -e '/inksvg\.py<.dependency/d' -e '/ruida\.py<.dependency/d' -i $@

thunderlaser.py:
	sed >  $@ -e '/INLINE_BLOCK_START/,$$d' < src/ruida-laser.py
	sed >> $@ -e '/if __name__ ==/,$$d' < src/inksvg.py
	sed >> $@ -e '/if __name__ ==/,$$d' < src/ruida.py
	sed >> $@ -e '1,/INLINE_BLOCK_END/d' < src/ruida-laser.py

#install is used by dist.
install:
	mkdir -p $(DEST)
	# CAUTION: cp -a does not work under fakeroot. Use cp -r instead.
	install -m 755 -t $(DEST) *.py
	install -m 644 -t $(DEST) *.inx
	mkdir -p $(UDEV)/rules.d
	install -m 644 -T thunderlaser-udev.rules $(UDEV)/rules.d/40-thunderlaser-udev.rules
	install -m 644 -t $(UDEV) thunderlaser-icon.png
	install -m 644 -t $(UDEV) thunderlaser-udev-notify.sh


tar_dist_classic: clean
	name=$(DISTNAME)-$(VERS); echo "$$name"; echo; \
	tar jcvf $$name.tar.bz2 $(EXCL) --transform="s,^,$$name/," $(ALL)
	grep about_version ./sendto_silhouette.inx 
	@echo version should be $(VERS)

tar_dist:
	python setup.py sdist --format=bztar
	mv dist/*.tar* .
	rm -rf dist

clean:
	rm -f thunderlaser.py thunderlaser.inx
	rm -f *.orig */*.orig
	rm -rf distribute/$(DISTNAME)
	rm -rf distribute/deb/files


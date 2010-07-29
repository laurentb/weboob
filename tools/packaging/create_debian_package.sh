#!/bin/sh
#
# This script generates one .deb packages for Weboob.
# It is based on python-stdeb setuptools extension.
#
# To accelerate the procedure, it is advised to disable the stdeb
# automatic depencies search feature.
# This requires a patch:
# # patch -p0 < stdeb.patch

[ ! -d /usr/share/pyshared/stdeb ] && echo 'Please install the python-stdeb package' && exit

FILEPATH="$1"

DIST_DIRPATH="$PWD/dist"
SCRIPT_DIRPATH=$(dirname $(readlink -f "$0"))

PKGNAME=$(basename $FILEPATH .py)
rm -f MANIFEST.in
MANIFEST_IN=$SCRIPT_DIRPATH/MANIFEST.in.d/$PKGNAME
[ -f $MANIFEST_IN ] && ln -s $MANIFEST_IN MANIFEST.in
README=$SCRIPT_DIRPATH/README.d/$PKGNAME
[ -f $README ] && mv README README.old && ln -s $README README
python $FILEPATH sdist
cd $DIST_DIRPATH
TARGZ=$(ls weboob-$PKGNAME-*.tar.gz)
tar xf $TARGZ
TARGZ_DIRPATH=$(basename $TARGZ .tar.gz)
[ ! -d $TARGZ_DIRPATH ] && echo "$TARGZ_DIRPATH not found" && exit
cd $TARGZ_DIRPATH
ln -s $FILEPATH setup.py
[ -f $MANIFEST_IN ] && ln -sf $MANIFEST_IN MANIFEST.in
# rm -f MANIFEST.in
python setup.py --command-packages=stdeb.command sdist_dsc --extra-cfg-file $SCRIPT_DIRPATH/stdeb.cfg
[ ! -d deb_dist/$TARGZ_DIRPATH ] && echo "deb_dist/$TARGZ_DIRPATH not found" && exit
cd deb_dist/$TARGZ_DIRPATH
dpkg-buildpackage -rfakeroot
cd ..
[ ! -f *.deb ] && echo "Debian package not found" && exit
mv *.deb *.diff.gz *.changes *.orig.tar.gz $DEB_DIRPATH
cd ../../..
[ -f $README ] && mv README.old README

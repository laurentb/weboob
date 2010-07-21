#!/bin/sh
#
# This script generates the .deb packages for Weboob.
# It is based on python-stdeb setuptools extension.
#
# To accelerate the procedure, it is advised to disable the stdeb
# automatic depencies search feature.
# This requires a patch:
# # patch -p0 < stdeb.patch

[ ! -d /usr/share/pyshared/stdeb ] && echo 'Please install the python-stdeb package' && exit

DEB_DIRPATH="$PWD/deb"
DIST_DIRPATH="$PWD/dist"
SCRIPT_DIRPATH=$(dirname $(readlink -f "$0"))

SETUP_PY_LIST="
$SCRIPT_DIRPATH/setup.py.d/core.py
$SCRIPT_DIRPATH/setup.py.d/core-qt.py
$SCRIPT_DIRPATH/setup.py.d/core-webkit-formatter.py

$SCRIPT_DIRPATH/setup.py.d/backends-bank.py
$SCRIPT_DIRPATH/setup.py.d/backends-dating.py
$SCRIPT_DIRPATH/setup.py.d/backends-messages.py
$SCRIPT_DIRPATH/setup.py.d/backends-torrent.py
$SCRIPT_DIRPATH/setup.py.d/backends-travel.py
$SCRIPT_DIRPATH/setup.py.d/backends-video.py
$SCRIPT_DIRPATH/setup.py.d/backends-video-nsfw.py
$SCRIPT_DIRPATH/setup.py.d/backends-weather.py

$SCRIPT_DIRPATH/setup.py.d/boobank.py
$SCRIPT_DIRPATH/setup.py.d/havesex.py
$SCRIPT_DIRPATH/setup.py.d/masstransit.py
$SCRIPT_DIRPATH/setup.py.d/monboob.py
$SCRIPT_DIRPATH/setup.py.d/qboobmsg.py
$SCRIPT_DIRPATH/setup.py.d/qhavesex.py
$SCRIPT_DIRPATH/setup.py.d/qvideoob.py
$SCRIPT_DIRPATH/setup.py.d/qweboobcfg.py
$SCRIPT_DIRPATH/setup.py.d/travel.py
$SCRIPT_DIRPATH/setup.py.d/videoob.py
$SCRIPT_DIRPATH/setup.py.d/videoob_web.py
$SCRIPT_DIRPATH/setup.py.d/weboorrents.py
$SCRIPT_DIRPATH/setup.py.d/wetboobs.py
"

rm -rf $DEB_DIRPATH $DIST_DIRPATH MANIFEST.in *.egg-info
mkdir $DEB_DIRPATH

for f in $SETUP_PY_LIST
do
    echo "========== Creating Debian package for $f"
    PKGNAME=$(basename $f .py)
    rm -f MANIFEST.in
    MANIFEST_IN=$SCRIPT_DIRPATH/MANIFEST.in.d/$PKGNAME
    [ -f $MANIFEST_IN ] && ln -s $MANIFEST_IN MANIFEST.in
    README=$SCRIPT_DIRPATH/README.d/$PKGNAME
    [ -f $README ] && mv README README.old && ln -s $README README
    python $f sdist
    cd $DIST_DIRPATH
    TARGZ=$(ls weboob-$PKGNAME-*.tar.gz)
    tar xf $TARGZ
    TARGZ_DIRPATH=$(basename $TARGZ .tar.gz)
    [ ! -d $TARGZ_DIRPATH ] && echo "$TARGZ_DIRPATH not found" && exit
    cd $TARGZ_DIRPATH
    ln -s $f setup.py
    [ -f $MANIFEST_IN ] && ln -sf $MANIFEST_IN MANIFEST.in
    python setup.py --command-packages=stdeb.command sdist_dsc --extra-cfg-file $SCRIPT_DIRPATH/stdeb.cfg
    [ ! -d deb_dist/$TARGZ_DIRPATH ] && echo "deb_dist/$TARGZ_DIRPATH not found" && exit
    cd deb_dist/$TARGZ_DIRPATH
    fakeroot dpkg-buildpackage
    cd ..
    [ ! -f *.deb ] && echo "Debian package not found" && exit
    mv *.deb *.diff.gz *.changes *.orig.tar.gz $DEB_DIRPATH
    cd ../../..
    [ -f $README ] && mv README.old README
    pwd
    # break
done

# rm -rf $DIST_DIRPATH MANIFEST.in *.egg-info

echo
echo "Packages are in the $DEB_DIRPATH directory"

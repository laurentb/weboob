#!/bin/sh

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
    rm -rf $DIST_DIRPATH
    MANIFEST_IN=$SCRIPT_DIRPATH/MANIFEST.in.d/$(basename $f .py)
    [ -f $MANIFEST_IN ] && ln -s $MANIFEST_IN MANIFEST.in
    python $f sdist
    cd $DIST_DIRPATH
    TARGZ=$(ls *.tar.gz)
    tar xf $TARGZ
    PKGNAME=$(basename $f .py)
    TARGZ_DIRPATH=$(basename $TARGZ .tar.gz)
    cd $TARGZ_DIRPATH
    ln -s $f setup.py
    [ -f $MANIFEST_IN ] && ln -s $MANIFEST_IN MANIFEST.in
    python setup.py --command-packages=stdeb.command sdist_dsc --extra-cfg-file $SCRIPT_DIRPATH/stdeb.cfg
    cd deb_dist/$TARGZ_DIRPATH
    fakeroot dpkg-buildpackage
    cd ..
    mv *.deb *.diff.gz *.changes *.orig.tar.gz $DEB_DIRPATH
    cd ../../..
    # break
done

rm -rf $DIST_DIRPATH MANIFEST.in *.egg-info

echo
echo "Packages are in the $DEB_DIRPATH directory"

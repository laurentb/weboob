#!/usr/bin/env bash
# This script is used to release a version.
set -e

function set_version {
	echo -n "Replacing version in source files to $1"
	for fl in $(find . -iregex ".*\.\(py\|rst\)$" ! -path "./contrib/*"); do
        sed "s/^\(\s*\)\(VERSION\|version\|release\)\( *\)=\( *\)[\"'][0-9]\+\..\+[\"']\(,\?\)$/\1\2\3=\4'$1'\5/g" $fl > $fl.new
		diff $fl.new $fl >/dev/null && echo -n "." || echo -n "+"
		cp -f $fl.new $fl
		rm -f $fl.new
	done

	echo -e " done.\n"
}

if [ "$1" = "" ]; then
	echo "Syntax: $0 VERSION"
	exit 1
fi

VERSION=$1

export LANG=en_US.utf8
mv ChangeLog ChangeLog.old
echo -e "Weboob $VERSION (`date +%Y-%m-%d`)\n\t \n\n" > ChangeLog
cat ChangeLog.old >> ChangeLog
rm -f ChangeLog.old

vi +2 ChangeLog

set_version $VERSION

echo "Building Qt applications..."
./setup.py --qt sdist bdist clean -a || exit 1

echo "Generating manpages..."
tools/make_man.sh
echo -e "done!\n"

# in case there are new manpages not included in the git tree.
git add man/*

echo "Release commit:"
git commit -a -m "Weboob $VERSION released"
echo -ne "\n"

echo "Release tag:"
git tag $VERSION -s -m "Weboob $VERSION"
echo -ne "\n"

echo -n "Generating archive.. "
git archive HEAD --prefix=weboob-$VERSION/ -o weboob-$VERSION.tar
gzip -f weboob-$VERSION.tar
md5sum weboob-$VERSION.tar.gz

echo -ne "\nDo you want to change the version number (y/n) "
read change_version

if [ "$change_version" = "y" ]; then
	echo -n "Enter the new version number: "
	read NEW_VERSION
	set_version $NEW_VERSION
	git commit -a -m "bump to $NEW_VERSION"
fi

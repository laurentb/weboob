#!/bin/bash
# Usage: weboob$ tools/generate_changelog_modules.sh TAG "list of hash" [show]


BEGIN=$1
EXCLUDE=$2
SHOW=$3

for a in modules/*
do 
	if [ -d $a ]
	then
		MODULE=`basename $a`
		LOG=`git log  --format="%H:::* %s"  --date-order --reverse "$BEGIN..HEAD"  -- $a`
		for b in $EXCLUDE
		do
			LOG=$(echo "$LOG" |grep -v $b)
		done
		if [ -n "$LOG" ]
		then
			if [ -n "$SHOW" ]
			then
				echo "$LOG" | awk -F ":::" '{print $1}' | git show --stdin
			else
				echo -e "\tModules: $MODULE"
				echo "$LOG" | awk -F ":::" '{print "\t"$2}' | sed "s/$MODULE: //" | sed "s/\[$MODULE\] //"
				echo ""
			fi
		fi
	fi
done

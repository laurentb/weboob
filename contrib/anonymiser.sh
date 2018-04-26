#!/bin/sh

# A special file with the list of words to replace. The format is one word per line, with a tabulation as separation
# Example:
# name	offuscatedname
# phonenumber	111111
anonymise_list="Anonymiser"

# Take the folder to anonymise as argument, and check if it is a folder
if [ $# -gt 0 ] && [ -d $1 ]
then
	dossier=$1
else
	echo "Usage: $0 FOLDER"
	echo "For example : $0 /tmp/weboob_session_NLSIls/freemobile/"
	exit 1
fi

if [ ! -f $anonymise_list ] 
then
	echo "Please create the $anonymise_list file (see documentation)"
	exit 1
fi

# remove potentials old files
find $dossier -name \*_anonymised -delete
rm -rf $dossier/Anonyme

for file_to_anonymise in `find $dossier -type f`
do
	file=$file_to_anonymise"_anonymised"	
	cp $file_to_anonymise $file
	
	cat $anonymise_list | tr '\t' '_' | while read line
	do
		to_replace=$(echo "$line"|cut -d_ -f1)
		replace_with=$(echo "$line"|cut -d_ -f2)
		sed -i "s%$to_replace%$replace_with%Ig" $file
	done 
done
mkdir $dossier/Anonyme

find $dossier -name \*_anonymised -exec mv \{\} $dossier/Anonyme \;

#!/bin/sh
# Rapport des comptes bancaires
# Liste l'intégralité des comptes dans Boobank, leurs dernières opérations et les opérations à venir
# et envoie ça par mail si --mail machin@example.tld est spécifié, sinon ça affiche
# (Compatible Debian Squeze)
# Public domain <BohwaZ>

SUBJECT="[Banques] Rapport des comptes"
TMPSTORAGE="/tmp/"

rm -f ${TMPSTORAGE}account*

boobank -q -f table list > ${TMPSTORAGE}account_list

ACCOUNTS=`cat ${TMPSTORAGE}account_list | fgrep '@' | awk '{print $2}'`

for i in $ACCOUNTS
do
	boobank -q -f table history "$i" > ${TMPSTORAGE}account_history_${i}
	boobank -q -f table coming "$i"  > ${TMPSTORAGE}account_coming_${i}
done

echo "Ceci est le rapport des comptes bancaires, généré automatiquement." > ${TMPSTORAGE}account_mail
echo >> ${TMPSTORAGE}account_mail
cat ${TMPSTORAGE}account_list >> ${TMPSTORAGE}account_mail
echo >> ${TMPSTORAGE}account_mail

for i in $ACCOUNTS
do
	echo "Dernières opérations sur le compte $i" >> ${TMPSTORAGE}account_mail
	echo >> ${TMPSTORAGE}account_mail
	cat ${TMPSTORAGE}account_history_${i} >> ${TMPSTORAGE}account_mail
	echo >> ${TMPSTORAGE}account_mail
	if [ -s ${TMPSTORAGE}account_coming_${i} ]
	then
		echo "Opérations à venir sur le compte $i" >> ${TMPSTORAGE}account_mail
		echo >> ${TMPSTORAGE}account_mail
		cat ${TMPSTORAGE}account_coming_${i} >> ${TMPSTORAGE}account_mail
	else
		echo "Pas d'opération à venir sur le compte $i" >> ${TMPSTORAGE}account_mail
	fi
        echo >> ${TMPSTORAGE}account_mail
done

if [ "$1" = "--mail" ]
then
        cat ${TMPSTORAGE}account_mail | mail -s "$SUBJECT" -a "Content-type: text/plain; charset=UTF-8" "$2"
else
        cat ${TMPSTORAGE}account_mail
fi

rm -f ${TMPSTORAGE}account*

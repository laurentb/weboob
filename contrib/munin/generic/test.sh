#!/bin/bash


# Like boobank-munin does
export cache_expire=7200
export HOME="/home/flo"
export capa="ICapBank"
export do="iter_accounts"
export import="from weboob.capabilities.bank import ICapBank"
export attribvalue="balance"
export title="Solde des comptes"

echo "========= ICapBank fetch"
cp ./generic-munin ./banbank
./banbank
echo "========= ICapBank config"
./banbank config
rm banbank


# Monitor water level in Dresden

export cache_expire=7200
export HOME="/home/flo"
export capa="ICapGauge"
export do="get_last_measure,501060-level"
export import="from weboob.capabilities.gauge import ICapGauge"
export attribvalue="level"
export title="Niveau de l'elbe"
export label="id"

echo "========= ICapGauge fetch"
cp ./generic-munin ./gauge
./gauge
echo "========= ICapGauge config"
./gauge config
rm gauge

# Monitor leclercmobile balance

export cache_expire=7200
export HOME="/home/flo"
export capa="ICapBill"
export do="get_balance,06XXXXXXXXXX@leclercmobile,leclercmobile"
export import="from weboob.capabilities.bill import ICapBill"
export attribvalue="price"
export title="Solde restant"
export vlabel="Solde"

echo "========= ICapBill fetch"
cp ./generic-munin ./bill
./bill
echo "========= ICapBill config"
./bill config
rm bill



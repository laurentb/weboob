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
export do="get_last_measure,501060-level,sachsen"
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

# Monitor water level of the Elbe in sachsen

export cache_expire=7200
export HOME=/home/flo
export capa=ICapGauge
export do=iter_gauges,Elbe,sachsen
export import="from weboob.capabilities.gauge import ICapGauge"
export attribvalue=sensors/lastvalue/level
export title="Niveau de l'elbe en Saxe"
export label="name"

echo "========= ICapGauge fetch"
cp ./generic-munin ./elbe
./elbe
echo "========= ICapGauge config"
./elbe config
rm elbe

unset label


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

# Monitor all balances of all subscriptions
export cache_expire=7200
export HOME="/home/flo"
export capa="ICapBill"
export do="get_balance"
export get_object_list="iter_subscription"
export import="from weboob.capabilities.bill import ICapBill"
export attribvalue="price"
export title="Solde restant"
export vlabel="Solde"

echo "========= ICapBill2 fetch"
cp ./generic-munin ./bill
./bill
echo "========= ICapBill2 config"
./bill config
rm bill

unset get_object_list

# Monitor temperature in Rennes

export cache_expire=7200
export HOME="/home/flo"
export capa="ICapWeather"
export do="get_current,619163,yahoo"
export import="from weboob.capabilities.weather import ICapWeather"
export attribvalue="temp/value"
export attribid="temp/id"
export label="id"
export title="Température à Rennes"
export vlabel="Température"

echo "========= ICapWeather fetch"
cp ./generic-munin ./rennes
./rennes
echo "========= ICapWeather config"
./rennes config
rm rennes

unset label
unset vlabel
unset title

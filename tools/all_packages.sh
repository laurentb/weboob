#!/bin/sh

SCRIPT_DIRNAME=$(dirname $0)

COMMAND="$1"

SETUP_PY_LIST="
$SCRIPT_DIRNAME/setup.py.d/setup-core.py

$SCRIPT_DIRNAME/setup.py.d/setup-bank-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-dating-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-messages-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-torrent-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-travel-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-video-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-video-nsfw-backends.py
$SCRIPT_DIRNAME/setup.py.d/setup-weather-backends.py

$SCRIPT_DIRNAME/setup.py.d/setup-boobank.py
$SCRIPT_DIRNAME/setup.py.d/setup-havesex.py
$SCRIPT_DIRNAME/setup.py.d/setup-masstransit.py
$SCRIPT_DIRNAME/setup.py.d/setup-monboob.py
$SCRIPT_DIRNAME/setup.py.d/setup-qboobmsg.py
$SCRIPT_DIRNAME/setup.py.d/setup-qhavesex.py
$SCRIPT_DIRNAME/setup.py.d/setup-qvideoob.py
$SCRIPT_DIRNAME/setup.py.d/setup-qweboobcfg.py
$SCRIPT_DIRNAME/setup.py.d/setup-travel.py
$SCRIPT_DIRNAME/setup.py.d/setup-videoob.py
$SCRIPT_DIRNAME/setup.py.d/setup-videoob_web.py
$SCRIPT_DIRNAME/setup.py.d/setup-weboorrents.py
$SCRIPT_DIRNAME/setup.py.d/setup-wetboobs.py
"

for f in $SETUP_PY_LIST
do
    python $f clean --all
    python $f "$COMMAND"
done

#!/bin/sh

SCRIPT_DIRNAME=$(dirname $0)

[ -z "$1" ] && echo "no command provided" && exit 1

COMMAND="$1"

SETUP_PY_LIST="
$SCRIPT_DIRNAME/setup.py.d/core.py
$SCRIPT_DIRNAME/setup.py.d/core-qt.py
$SCRIPT_DIRNAME/setup.py.d/core-webkit-formatter.py

$SCRIPT_DIRNAME/setup.py.d/backends-bank.py
$SCRIPT_DIRNAME/setup.py.d/backends-dating.py
$SCRIPT_DIRNAME/setup.py.d/backends-messages.py
$SCRIPT_DIRNAME/setup.py.d/backends-torrent.py
$SCRIPT_DIRNAME/setup.py.d/backends-travel.py
$SCRIPT_DIRNAME/setup.py.d/backends-video.py
$SCRIPT_DIRNAME/setup.py.d/backends-video-nsfw.py
$SCRIPT_DIRNAME/setup.py.d/backends-weather.py

$SCRIPT_DIRNAME/setup.py.d/boobank.py
$SCRIPT_DIRNAME/setup.py.d/havesex.py
$SCRIPT_DIRNAME/setup.py.d/masstransit.py
$SCRIPT_DIRNAME/setup.py.d/monboob.py
$SCRIPT_DIRNAME/setup.py.d/qboobmsg.py
$SCRIPT_DIRNAME/setup.py.d/qhavesex.py
$SCRIPT_DIRNAME/setup.py.d/qvideoob.py
$SCRIPT_DIRNAME/setup.py.d/travel.py
$SCRIPT_DIRNAME/setup.py.d/videoob.py
$SCRIPT_DIRNAME/setup.py.d/videoob_web.py
$SCRIPT_DIRNAME/setup.py.d/weboorrents.py
$SCRIPT_DIRNAME/setup.py.d/wetboobs.py
"

for f in $SETUP_PY_LIST
do
    python $f clean --all
    python $f "$COMMAND"
done

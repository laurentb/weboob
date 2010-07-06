#!/bin/sh

COMMAND="$1"

SETUP_PY_LIST="
weboob/setup.py
weboob/backends/setup.py
weboob/applications/boobank/setup.py
weboob/applications/masstransit/setup.py
weboob/applications/monboob/setup.py
weboob/applications/qboobmsg/setup.py
weboob/applications/qhavesex/setup.py
weboob/applications/qvideoob/setup.py
weboob/applications/travel/setup.py
weboob/applications/videoob/setup.py
weboob/applications/videoob_web/setup.py
weboob/applications/weboorrents/setup.py
weboob/applications/wetboobs/setup.py
"


for f in $SETUP_PY_LIST
do
    python $f clean --all
    python $f "$COMMAND"
done

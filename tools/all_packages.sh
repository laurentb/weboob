#!/bin/sh

COMMAND="$1"

SETUP_PY_LIST="
weboob/setup.py
weboob/backends/setup.py
weboob/frontends/boobank/setup.py
weboob/frontends/masstransit/setup.py
weboob/frontends/monboob/setup.py
weboob/frontends/qboobmsg/setup.py
weboob/frontends/qhavesex/setup.py
weboob/frontends/qvideoob/setup.py
weboob/frontends/travel/setup.py
weboob/frontends/videoob/setup.py
weboob/frontends/videoob_web/setup.py
weboob/frontends/weboorrents/setup.py
weboob/frontends/wetboobs/setup.py
"


for f in $SETUP_PY_LIST
do
    python $f clean --all
    python $f "$COMMAND"
done

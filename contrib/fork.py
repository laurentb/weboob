#! /usr/bin/python
# Licensed under WTFPL.
# https://linuxfr.org/users/shamanphenix/journaux/weboob-la-consecration#comment-1583941

from __future__ import print_function

import os
import sys
import base64
import subprocess
import ConfigParser

scripts_tr = [('boobank','bisoubank'),
              ('boobathon','bisouthon'),
              ('boobcoming','bisoucoming'),
              ('boobill','bisoubill'),
              ('booblyrics','bisoulyrics'),
              ('boobmsg', 'bisoumsg'),
              ('boobooks', 'bisoubooks'),
              ('boobsize', 'bisousize'),
              ('boobtracker', 'bisoutracker'),
              ('cineoob', 'cineisou'),
              ('comparoob', 'comparisou'),
              ('cookboob', 'cookbisou'),
              ('flatboob', 'flatbisou'),
              ('galleroob', 'gallerisou'),
              ('geolooc', 'geolooc'),
              ('handjoob', 'handjisou'),
              ('havedate', 'havedate'),
              ('monboob', 'monbisou'),
              ('parceloob', 'parcelisou'),
              ('pastoob', 'pastisou'),
              ('qboobmsg', 'qbisoumsg'),
              ('qboobtracker', 'qbisoutracker'),
              ('qcineoob', 'qcineisou'),
              ('qcookboob', 'qcookbisou'),
              ('qflatboob', 'qflatbisou'),
              ('qgalleroob', 'qgallerisou'),
              ('qhandjoob', 'qhandjisou'),
              ('qhavedate', 'qhavedate'),
              ('qvideoob', 'qvideisou'),
              ('qwebcontentedit', 'qwebpasmalintentedit'),
              ('radioob', 'radisou'),
              ('suboob', 'subisou'),
              ('translaboob', 'translabisou'),
              ('traveloob', 'travelisou'),
              ('videoob', 'videisou'),
              ('webcontentedit', 'webpasmalintentedit'),
              ('weboob-cli', 'webisounours-cli'),
              ('weboob-config', 'webisounours-config'),
              ('weboob-config-qt', 'webisounours-config-qt'),
              ('weboob-debug', 'webisounours-debug'),
              ('weboob-repos', 'webisounours-repos'),
              ('weboorrents', 'webisourrents'),
              ('wetboobs', 'wetbisous')]

icons_tr = [os.path.join('icons',i) for i in os.listdir('icons')]
modules_tr = [os.path.join('modules',i,'favicon.png') for i in os.listdir('modules')]

desktop_tr = [('qboobmsg.desktop','QBisoumsg'),
              ('qboobtracker.desktop','QBisouTracker'),
              ('qcineoob.desktop','QCineisou'),
              ('qcookboob.desktop','QCookbisou'),
              ('qflatboob.desktop','QFlatBisou'),
              ('qgalleroob.desktop','QGallerisou'),
              ('qhandjoob.desktop','QHandJisou'),
              ('qhavedate.desktop','QHaveDate'),
              ('qvideoob.desktop','QVideisou'),
              ('qwebcontentedit.desktop','QWebPasmalinTentEdit'),
             ]

mask = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wEODzYzz5PthwAAAB1pVFh0Q29tbWVudAAAAAAAQ3JlYXRlZCB3aXRoIEdJTVBkLmUHAAABsklEQVR42u3avyvEcRzH8adEXJKSOlFXStSVlDIow5UMBoOiDAyUwWAwSDIYlIG6EoPBYFAGSQZlUDdIKWUQJQxSIiElv7ow8K1L13V33oP35/t+1vsPeCyfu3p9wbIsy7Isy7K0FvIzvg/4BLr8iB/7wXvX7Cf83C/8J/AC1PgBv5oE7901UOYqvBDYSYH37gjIdw0fBE7SwHsXcwkfBm4zwHu34gI+Arxngfcuqhnf/Qd44rVrxA8L4Wc14meE8KMa8ctC+F5t8DxgWwAeB1q14UuBQwH8A1CvDV8NXAngz4FKbfgm4FkAvwcUacN3CD12Gxpf+kEh/IJG/KQQfkIjflEIP6ANngNs+vV/fTGwLwB/Ahq14UPAhQD+EqjShm8AHgXwB0CJNnwb8CGA3wJyteH7hR67JY0/c+NC+CmN+Hkh/JBG/JoQvlMbPADsCsBfUbjrlQOnAvgboFYbvh64E8Afo3THiwngYyje7wrIbKdzcrIKkt1eF8WhwsBbBvgRHCySJr4Hh0s1YsaBFnxQsjHzHqjDR00n4M+ACnzYOt/f6ASwLMuyLMuyLMv6x30B2yNJ8I8ofLMAAAAASUVORK5CYII=')
f = open('bisoumask.png','w')
f.write(mask)
f.close()

for i in icons_tr + modules_tr:
    try:
        subprocess.call('mogrify %s -blur 0x4 2> /dev/null > /dev/null' % i, shell=True)
        subprocess.call('composite bisoumask.png %s bisouresult.png 2> /dev/null > /dev/null' % i, shell=True)
        os.rename('bisouresult.png',i)
    except OSError:
        print("No picture named %s" % i, file=sys.stderr)

for s in scripts_tr:
    os.rename (os.path.join('scripts',s[0]),os.path.join('scripts',s[1]))

for d in desktop_tr:
    config = ConfigParser.ConfigParser()
    config.readfp(open(os.path.join('desktop',d[0])))
    config.set('Desktop Entry','Name',d[1])
    config.write(open(os.path.join('desktop',d[0]),'w'))

# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from datetime import datetime, date, time
from weboob.tools.browser import Browser
from weboob.tools.misc import toUnicode

class CanalTP(Browser):
    DOMAIN = 'widget.canaltp.fr'
    PROTOCOL = 'http'
    PAGES = {}

    def __init__(self):
        Browser.__init__(self, '')

    def iter_station_search(self, pattern):
        result = self.openurl(u"http://widget.canaltp.fr/Prochains_departs_15122009/dev/gare.php?txtrech=%s" % unicode(pattern)).read()
        for station in result.split('&'):
            try:
                _id, name = station.split('=')
            except ValueError:
                continue
            else:
                yield _id, toUnicode(name)

    def iter_station_departures(self, station_id, arrival_id=None):
        result = self.openurl(u"http://widget.canaltp.fr/Prochains_departs_15122009/dev/index.php?gare=%s" % unicode(station_id)).read()
        result = result
        departure = ''
        for line in result.split('&'):
            key, value = line.split('=', 1)
            if key == 'nomgare':
                departure = value
            elif key.startswith('ligne'):
                _type, unknown, _time, arrival, served, late, late_reason = value.split(';', 6)
                yield {'type':        toUnicode(_type),
                       'time':        datetime.combine(date.today(), time(*[int(x) for x in _time.split(':')])),
                       'departure':   toUnicode(departure),
                       'arrival':     toUnicode(arrival).strip(),
                       'late':        late and time(0, int(late.split()[0])) or time(),
                       'late_reason': toUnicode(late_reason).replace('\n', '').strip()}

    def home(self):
        pass

    def login(self):
        pass

    def is_logged(self):
        """ Do not need to be logged """
        return True

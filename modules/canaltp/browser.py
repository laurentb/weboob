# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from datetime import datetime, date, time

from weboob.deprecated.browser import Browser
from weboob.tools.misc import to_unicode
from weboob.deprecated.browser import BrokenPageError


__all__ = ['CanalTP']


class CanalTP(Browser):
    DOMAIN = 'widget.canaltp.fr'

    def __init__(self, **kwargs):
        Browser.__init__(self, '', **kwargs)

    def iter_station_search(self, pattern):
        url = u'http://widget.canaltp.fr/Prochains_departs_15122009/dev/gare.php?txtrech=%s' % unicode(pattern)
        result = self.openurl(url.encode('utf-8')).read()
        for station in result.split('&'):
            try:
                _id, name = station.split('=')
            except ValueError:
                continue
            else:
                yield _id, to_unicode(name)

    def iter_station_departures(self, station_id, arrival_id=None):
        url = u'http://widget.canaltp.fr/Prochains_departs_15122009/dev/index.php?gare=%s' % unicode(station_id)
        result = self.openurl(url.encode('utf-8')).read()
        result = result
        departure = ''
        for line in result.split('&'):
            if '=' not in line:
                raise BrokenPageError('Unable to parse result: %s' % line)
            key, value = line.split('=', 1)
            if key == 'nomgare':
                departure = value
            elif key.startswith('ligne'):
                _type, unknown, _time, arrival, served, late, late_reason = value.split(';', 6)
                yield {'type':        to_unicode(_type),
                       'time':        datetime.combine(date.today(), time(*[int(x) for x in _time.split(':')])),
                       'departure':   to_unicode(departure),
                       'arrival':     to_unicode(arrival).strip(),
                       'late':        late and time(0, int(late.split()[0])) or time(),
                       'late_reason': to_unicode(late_reason).replace('\n', '').strip()}

    def home(self):
        pass

    def login(self):
        pass

    def is_logged(self):
        """ Do not need to be logged """
        return True

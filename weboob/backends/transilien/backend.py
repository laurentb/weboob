# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Hébert, Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.capabilities.travel import ICapTravel, Station, Departure
from weboob.tools.backend import BaseBackend

from .browser import Transilien
from .stations import STATIONS

class TransilienBackend(BaseBackend, ICapTravel):
    NAME = 'transilien'
    MAINTAINER = u'Julien Hébert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.7'
    LICENSE = 'GPLv3'
    DESCRIPTION = "Transports in Paris"
    BROWSER = Transilien

    def iter_station_search(self, pattern):
        pattern = pattern.lower()
        for _id, name in STATIONS.iteritems():
            if name.lower().find(pattern) >= 0:
                yield Station(_id, name)

    def iter_station_departures(self, station_id, arrival_id=None):
        for i, d in enumerate(self.browser.iter_station_departures(station_id, arrival_id)):
            departure = Departure(i, d['type'], d['time'])
            departure.departure_station = d['departure']
            departure.arrival_station = d['arrival']
            departure.late = d['late']
            departure.information = d['late_reason']
            departure.plateform = d['plateform']
            yield departure

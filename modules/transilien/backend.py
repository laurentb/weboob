# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Hébert, Romain Bignon
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




from weboob.capabilities.travel import ICapTravel, Station, Departure, RoadStep
from weboob.tools.backend import BaseBackend

from .browser import Transilien
from .stations import STATIONS


class TransilienBackend(BaseBackend, ICapTravel):
    NAME = 'transilien'
    MAINTAINER = u'Julien Hébert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Public transportation in the Paris area"
    BROWSER = Transilien

    def iter_station_search(self, pattern):
        pattern = pattern.lower()
        for _id, name in STATIONS.iteritems():
            if name.lower().find(pattern) >= 0:
                yield Station(_id, name)

    def iter_station_departures(self, station_id, arrival_id=None, date=None):
        with self.browser:
            for i, d in enumerate(self.browser.iter_station_departures(station_id, arrival_id)):
                departure = Departure(i, d['type'], d['time'])
                departure.departure_station = d['departure']
                departure.arrival_station = d['arrival']
                departure.late = d['late']
                departure.information = d['late_reason']
                departure.plateform = d['plateform']
                yield departure

    def iter_roadmap(self, departure, arrival, filters):
        with self.browser:
            roadmap = self.browser.get_roadmap(departure, arrival, filters)

        for s in roadmap['steps']:
            step = RoadStep(s['id'])
            step.line = s['line']
            step.start_time = s['start_time']
            step.end_time = s['end_time']
            step.departure = s['departure']
            step.arrival = s['arrival']
            step.duration = s['duration']
            yield step

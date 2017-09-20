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

from weboob.capabilities.travel import CapTravel, Station, Departure
from weboob.tools.backend import Module

from .browser import CanalTP


__all__ = ['CanalTPModule']


class CanalTPModule(Module, CapTravel):
    NAME = 'canaltp'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = "French trains"
    BROWSER = CanalTP

    def iter_station_search(self, pattern):
        for _id, name in self.browser.iter_station_search(pattern):
            yield Station(_id, name)

    def iter_station_departures(self, station_id, arrival_id=None, date=None):
        for i, d in enumerate(self.browser.iter_station_departures(station_id, arrival_id)):
            departure = Departure(i, d['type'], d['time'])
            departure.departure_station = d['departure']
            departure.arrival_station = d['arrival']
            departure.late = d['late']
            departure.information = d['late_reason']
            yield departure

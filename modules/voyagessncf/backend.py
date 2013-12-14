# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


from weboob.tools.backend import BaseBackend
from weboob.capabilities.travel import ICapTravel, Station, Departure
from weboob.capabilities import UserError

from .browser import VoyagesSNCFBrowser


__all__ = ['VoyagesSNCFBackend']


class VoyagesSNCFBackend(BaseBackend, ICapTravel):
    NAME = 'voyagessncf'
    DESCRIPTION = u'Voyages SNCF'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    LICENSE = 'AGPLv3+'
    VERSION = '0.h'

    BROWSER = VoyagesSNCFBrowser
    STATIONS = []

    def _populate_stations(self):
        if len(self.STATIONS) == 0:
            with self.browser:
                self.STATIONS = self.browser.get_stations()

    def iter_station_search(self, pattern):
        self._populate_stations()

        pattern = pattern.lower()
        for _id, name in enumerate(self.STATIONS):
            if name.lower().startswith(pattern):
                yield Station(_id, unicode(name))

    def iter_station_departures(self, station_id, arrival_id=None, date=None):
        self._populate_stations()

        if arrival_id is None:
            raise UserError('The arrival station is required')

        try:
            station = self.STATIONS[int(station_id)]
            arrival = self.STATIONS[int(arrival_id)]
        except (IndexError, ValueError):
            raise UserError('Unknown station')

        with self.browser:
            for i, d in enumerate(self.browser.iter_departures(station, arrival, date)):
                departure = Departure(i, d['type'], d['time'])
                departure.departure_station = d['departure']
                departure.arrival_station = d['arrival']
                departure.arrival_time = d['arrival_time']
                departure.price = d['price']
                departure.currency = d['currency']
                yield departure

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

from collections import OrderedDict

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.capabilities.travel import CapTravel, Station, Departure
from weboob.capabilities import UserError

from .browser import VoyagesSNCFBrowser


__all__ = ['VoyagesSNCFModule']


class VoyagesSNCFModule(Module, CapTravel):
    NAME = 'voyagessncf'
    DESCRIPTION = u'Voyages SNCF'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(Value('age', label='Passenger age', default='ADULT',
                                 choices=OrderedDict((('ADULT', '26-59 ans'),
                                                      ('SENIOR', '60 et +'),
                                                      ('YOUNG', '12-25 ans'),
                                                      ('CHILD_UNDER_FOUR', '0-3 ans'),
                                                      ('CHILDREN', '4-11 ans')))),
                           Value('card', label='Passenger card', default='default',
                                 choices=OrderedDict((('default', u'Pas de carte'),
                                                      ('YOUNGS', u'Carte Jeune'),
                                                      ('ESCA', u'Carte Escapades'),
                                                      ('WEEKE', u'Carte Week-end'),
                                                      ('FQ2ND', u'Abo Fréquence 2e'),
                                                      ('FQ1ST', u'Abo Fréquence 1e'),
                                                      ('FF2ND', u'Abo Forfait 2e'),
                                                      ('FF1ST', u'Abo Forfait 1e'),
                                                      ('ACCWE', u'Accompagnant Carte Week-end'),
                                                      ('ACCCHD', u'Accompagnant Carte Enfant+'),
                                                      ('ENFAM', u'Carte Enfant Famille'),
                                                      ('FAM30', u'Carte Familles Nombreuses 30%'),
                                                      ('FAM40', u'Carte Familles Nombreuses 40%'),
                                                      ('FAM50', u'Carte Familles Nombreuses 50%'),
                                                      ('FAM75', u'Carte Familles Nombreuses 75%'),
                                                      ('MI2ND', u'Carte Militaire 2e'),
                                                      ('MI1ST', u'Carte Militaire 1e'),
                                                      ('MIFAM', u'Carte Famille Militaire'),
                                                      ('THBIZ', u'Thalys ThePass Business'),
                                                      ('THPREM', u'Thalys ThePass Premium'),
                                                      ('THWE', u'Thalys ThePass Weekend')))),
                           Value('class', label='Comfort class', default='2',
                                 choices=OrderedDict((('1', u'1e classe'),
                                                      ('2', u'2e classe')))))

    BROWSER = VoyagesSNCFBrowser
    STATIONS = []

    def _populate_stations(self):
        if len(self.STATIONS) == 0:
            with self.browser:
                self.STATIONS = self.browser.get_stations()

    def iter_station_search(self, pattern):
        self._populate_stations()

        pattern = pattern.lower()
        already = set()

        # First stations whose name starts with pattern...
        for _id, name in enumerate(self.STATIONS):
            if name.lower().startswith(pattern):
                already.add(_id)
                yield Station(_id, unicode(name))
        # ...then ones whose name contains pattern.
        for _id, name in enumerate(self.STATIONS):
            if pattern in name.lower() and _id not in already:
                yield Station(_id, unicode(name))

    def iter_station_departures(self, station_id, arrival_id=None, date=None):
        self._populate_stations()

        if arrival_id is None:
            raise UserError('The arrival station is required')

        try:
            station = self.STATIONS[int(station_id)]
            arrival = self.STATIONS[int(arrival_id)]
        except (IndexError, ValueError):
            try:
                station = list(self.iter_station_search(station_id))[0].name
                arrival = list(self.iter_station_search(arrival_id))[0].name
            except IndexError:
                raise UserError('Unknown station')

        with self.browser:
            for i, d in enumerate(self.browser.iter_departures(station, arrival, date,
                                                               self.config['age'].get(),
                                                               self.config['card'].get(),
                                                               self.config['class'].get())):
                departure = Departure(i, d['type'], d['time'])
                departure.departure_station = d['departure']
                departure.arrival_station = d['arrival']
                departure.arrival_time = d['arrival_time']
                departure.price = d['price']
                departure.currency = d['currency']
                departure.information = d['price_info']
                yield departure

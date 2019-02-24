# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Hébert, Romain Bignon
# Copyright(C) 2014 Benjamin Carton
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from weboob.capabilities.travel import CapTravel
from weboob.tools.backend import Module

from .browser import Transilien


class TransilienModule(Module, CapTravel):
    NAME = 'transilien'
    MAINTAINER = u'Julien Hébert'
    EMAIL = 'juke@free.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Public transportation in the Paris area"
    BROWSER = Transilien

    def iter_station_search(self, pattern):
        return self.browser.get_stations(pattern)

    def iter_station_departures(self, station_id, arrival_id=None, date=None):
        return self.browser.get_station_departues(station_id.replace('-', ' '), arrival_id, date)

    def iter_roadmap(self, departure, arrival, filters):
        return self.browser.get_roadmap(departure, arrival, filters)

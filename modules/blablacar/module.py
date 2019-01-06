# -*- coding: utf-8 -*-

# Copyright(C) 2015      Bezleputh
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


from weboob.tools.backend import Module
from weboob.capabilities.travel import CapTravel

from .browser import BlablacarBrowser


__all__ = ['BlablacarModule']


class BlablacarModule(Module, CapTravel):
    NAME = 'blablacar'
    DESCRIPTION = u'blablacar website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = BlablacarBrowser

    def iter_roadmap(self, departure, arrival, filters):
        return self.browser.get_roadmap(departure, arrival, filters)

    def iter_station_departures(self, station_id, arrival_id, date):
        return self.browser.get_station_departures(station_id, arrival_id, date)

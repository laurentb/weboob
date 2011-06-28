# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Julien Hébert
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


import logging

from weboob.capabilities.travel import ICapTravel
from weboob.tools.application.repl import ReplApplication


__all__ = ['Traveloob']


class Traveloob(ReplApplication):
    APPNAME = 'traveloob'
    VERSION = '0.9'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to search for train stations and get departure times.'
    CAPS = ICapTravel
    DEFAULT_FORMATTER = 'table'

    def do_stations(self, pattern):
        """
        stations PATTERN

        Search stations.
        """
        for backend, station in self.do('iter_station_search', pattern):
            self.format(station)
        self.flush()

    def do_departures(self, line):
        """
        departures STATION [ARRIVAL]

        List all departures for a given station.
        """
        station, arrival = self.parse_command_args(line, 2, 1)

        station_id, backend_name = self.parse_id(station)
        if arrival:
            arrival_id, backend_name2 = self.parse_id(arrival)
            if backend_name and backend_name2 and backend_name != backend_name2:
                logging.error('Departure and arrival aren\'t on the same backend')
                return 1
        else:
            arrival_id = backend_name2 = None

        if backend_name:
            backends = [backend_name]
        elif backend_name2:
            backends = [backend_name2]
        else:
            backends = None

        for backend, departure in self.do('iter_station_departures', station_id, arrival_id, backends=backends):
            self.format(departure)
        self.flush()

    def do_roadmap(self, line):
        departure, arrival = self.parse_command_args(line, 2, 2)

        for backend, route in self.do('iter_roadmap', departure, arrival):
            self.format(route)
        self.flush()

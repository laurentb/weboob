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


import sys
from datetime import datetime
import logging

from weboob.capabilities.travel import ICapTravel, RoadmapFilters
from weboob.tools.application.repl import ReplApplication


__all__ = ['Traveloob']


class Traveloob(ReplApplication):
    APPNAME = 'traveloob'
    VERSION = '0.e'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon'
    DESCRIPTION = 'Console application allowing to search for train stations and get departure times.'
    CAPS = ICapTravel
    DEFAULT_FORMATTER = 'table'

    def add_application_options(self, group):
        group.add_option('--departure-time')
        group.add_option('--arrival-time')

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
        """
        roadmap DEPARTURE ARRIVAL

        Display the roadmap to travel from DEPARTURE to ARRIVAL.

        Command-line parameters:
           --departure-time TIME    requested departure time
           --arrival-time TIME      requested arrival time

        TIME might be in form "yyyy-mm-dd HH:MM" or "HH:MM".

        Example:
            > roadmap Puteaux Aulnay-sous-Bois --arrival-time 22:00
        """
        departure, arrival = self.parse_command_args(line, 2, 2)

        filters = RoadmapFilters()
        try:
            filters.departure_time = self.parse_datetime(self.options.departure_time)
            filters.arrival_time = self.parse_datetime(self.options.arrival_time)
        except ValueError, e:
            print >>sys.stderr, 'Invalid datetime value: %s' % e
            print >>sys.stderr, 'Please enter a datetime in form "yyyy-mm-dd HH:MM" or "HH:MM".'
            return 1

        for backend, route in self.do('iter_roadmap', departure, arrival, filters):
            self.format(route)
        self.flush()

    def parse_datetime(self, text):
        if text is None:
            return None

        try:
            date = datetime.strptime(text, '%Y-%m-%d %H:%M')
        except ValueError:
            try:
                date = datetime.strptime(text, '%H:%M')
            except ValueError:
                raise ValueError(text)
            date = datetime.now().replace(hour=date.hour, minute=date.minute)

        return date

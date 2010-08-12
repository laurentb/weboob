# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Julien Hébert
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


import logging

from weboob.capabilities.travel import ICapTravel
from weboob.tools.application.console import ConsoleApplication


__all__ = ['Traveloob']


class Traveloob(ConsoleApplication):
    APPNAME = 'traveloob'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Search stations')
    def command_stations(self, pattern):
        self.load_backends(ICapTravel)
        for backend, station in self.do('iter_station_search', pattern):
            self.format(station)

    @ConsoleApplication.command('List all departures for a given station')
    def command_departures(self, station, arrival=None):
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

        self.load_backends(ICapTravel, names=backends)
        for backend, departure in self.do('iter_station_departures', station_id, arrival_id):
            self.format(departure)

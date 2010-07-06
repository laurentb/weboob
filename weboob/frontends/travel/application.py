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


from weboob.capabilities.travel import ICapTravel
from weboob.tools.application import ConsoleApplication


__all__ = ['Travel']


class Travel(ConsoleApplication):
    APPNAME = 'travel'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        self.load_modules(ICapTravel)

        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Search stations')
    def command_stations(self, pattern):
        for backend, station in self.weboob.do('iter_station_search', pattern):
            self.format(station, backend.name)

    @ConsoleApplication.command('List all departures for a given station')
    def command_departures(self, station, arrival=None):
        for backend, departure in self.weboob.do('iter_station_departures', station, arrival):
            self.format(departure, backend.name)

# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon, Julien Hébert

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.capabilities.travel import ICapTravel
from weboob.tools.application import ConsoleApplication

class Travel(ConsoleApplication):
    APPNAME = 'travel'

    def main(self, argv):
        self.weboob.load_modules(ICapTravel)

        return self.process_command(*argv[1:])

    @ConsoleApplication.command('Search stations')
    def command_stations(self, pattern):
        print ".--------------------------------.---------------------------------------------."
        print '| ID                             | Name                                        |'
        print '+--------------------------------+---------------------------------------------+'
        count = 0
        for backend in self.weboob.iter_backends():
            for station in backend.iter_station_search(pattern):
                print '| %-31s| %-44s|' % (station.id, station.name)
                count += 1
        print "+--------------------------------'---------------------------------------------+"
        print "| %3d stations listed                                                          |" % count
        print "'------------------------------------------------------------------------------'"

    @ConsoleApplication.command('List all departures on a special station')
    def command_departures(self, station, arrival=None):
        print ".-----.-----------.-------.-----------------------.-------.--------------------.------------"
        print "| ID  | Type      | Time  | Arrival               | Late  | Info               | Plateform |"
        print "+-----+-----------+-------+-----------------------+-------+--------------------+-----------+"
        count = 0
        for backend in self.weboob.iter_backends():
            for departure in backend.iter_station_departures(station, arrival):
                print u"|%4d | %-10s|%6s | %-22s|%6s | %-19s| %-10s|" % (departure.id,
                                                                   departure.type,
                                                                   departure.time.strftime("%H:%M"),
                                                                   departure.arrival_station,
                                                                   departure.late and departure.late.strftime("%H:%M") or '',
                                                                   departure.information,
                                                                   departure.plateform)
                count += 1
        print "+-----'-----------'-------'-----------------------'-------'--------------------'-----------+"
        print "| %3d departures listed                                                                    |" % count
        print "'------------------------------------------------------------------------------------------'"

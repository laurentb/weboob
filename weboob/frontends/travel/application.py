# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

import sys
from types import MethodType

from weboob import Weboob
from weboob.capabilities.travel import ICapTravel
from weboob.tools.application import ConsoleApplication

class Travel(ConsoleApplication):
    APPNAME = 'travel'

    def main(self, argv):
        self.weboob.load_modules(ICapTravel)

        if len(argv) == 1:
            print >>sys.stderr, "Usage: %s <command> [args ...]" % argv[0]
            return -1

        return self.command(argv[1], *argv[2:])

    def getMethods(self, prefix):
        services = {}
        for attrname in dir(self):
            if not attrname.startswith(prefix):
                continue
            attr = getattr(self, attrname)
            if not isinstance(attr, MethodType):
                continue
            name = attrname[len(prefix):]
            services[name] = attr
        return services

    def command(self, command, *args):
        commands = self.getMethods('command_')
        if not command in commands:
            print >>sys.stderr, "No such command: %s" % command
            self.command_help()
            return 1
        try:
            return commands[command](*args)
        except TypeError, e:
            try:
                print >>sys.stderr, "Command %s takes %s arguments" % (command, int(str(e).split(' ')[3]) - 1)
            except:
                print >>sys.stderr, '%s' % e
            return 1

    def command_help(self):
        print 'Available commands are:'
        print '      stations <pattern>              Search stations'
        print '      departures <station> [arrival]  List all departures on a special station'

    def command_stations(self, pattern):
        print ".--------------------------------.---------------------------------------------."
        print '| ID                             | Name                                        |'
        print '+--------------------------------+---------------------------------------------+'
        count = 0
        for name, backend, in self.weboob.iter_backends():
            for station in backend.iter_station_search(pattern):
                print '| %-30s | %-43s |' % (station.id, station.name)
                count += 1
        print "+--------------------------------'---------------------------------------------+"
        print "| %3d stations listed                                                          |" % count
        print "'------------------------------------------------------------------------------'"

    def command_departures(self, station, arrival_station=None):
        print ".-----.-----------.-------.-----------------------.-------.--------------------."
        print "| ID  | Type      | Time  | Arrival               | Late  | Info               |"
        print "+-----+-----------+-------+-----------------------+-------+--------------------+"
        count = 0
        for name, backend, in self.weboob.iter_backends():
            for departure in backend.iter_station_departures(station, arrival_station):
                print u"| %3d | %-9s | %5s | %-21s | %5s | %-18s |" % (departure.id,
                                                                   departure.type,
                                                                   departure.time.strftime("%H:%M"),
                                                                   departure.arrival_station,
                                                                   departure.late and departure.late.strftime("%H:%M") or '',
                                                                   departure.information)
                count += 1
        print "+-----'-----------'-------'-----------------------'-------'--------------------+"
        print "| %3d departures listed                                                        |" % count
        print "'------------------------------------------------------------------------------'"

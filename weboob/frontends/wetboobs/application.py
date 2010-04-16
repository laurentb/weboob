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

from weboob.capabilities.weather import ICapWeather, CityNotFound
from weboob.tools.application import ConsoleApplication

class WetBoobs(ConsoleApplication):
    APPNAME = 'wetboobs'

    def main(self, argv):
        self.weboob.load_modules(ICapWeather)

        return self.process_command(*argv[1:])

    @ConsoleApplication.command('search cities')
    def command_search(self, pattern):
        print ".--------------------------------.---------------------------------------------."
        print '| ID                             | Name                                        |'
        print '+--------------------------------+---------------------------------------------+'
        count = 0
        for backend, in self.weboob.iter_backends():
            for city in backend.iter_city_search(pattern):
                print u'| %-31s| %-44s|' % (city.city_id, city.name)
                count += 1
        print "+--------------------------------'---------------------------------------------+"
        print "| %3d cities listed                                                            |" % count
        print "'------------------------------------------------------------------------------'"

    @ConsoleApplication.command('get current weather')
    def command_current(self, city):
        print ".-------------.----------------------------------------------------------------."
        print '| Temperature | Text                                                           |'
        print '+-------------+----------------------------------------------------------------+'
        found = 0
        for backend, in self.weboob.iter_backends():
            try:
                current = backend.get_current(city)
                print u'| %-12s| %-63s|' % (u'%d °%s' % (current.temp, current.unit), current.text)
                found = 1
            except CityNotFound:
                if not found:
                    found = -1
        if found < 0:
            print "|          -- | City not found                                                 |"
        print "+-------------'----------------------------------------------------------------+"

    @ConsoleApplication.command('get forecasts')
    def command_forecasts(self, city):
        print ".-------------.------.------.--------------------------------------------------."
        print '| Date        |   Min |   Max | Text                                           |'
        print '+-------------+-------+-------+------------------------------------------------+'
        found = 0
        for backend, in self.weboob.iter_backends():
            try:
                for f in backend.iter_forecast(city):
                    found = 1
                    print u'| %-12s|%6s |%6s | %-47s|' % (f.date,
                                                         u'%d °%s' % (f.low, f.unit),
                                                         u'%d °%s' % (f.high, f.unit),
                                                         f.text)
            except CityNotFound:
                if not found:
                    found = -1
        if found < 0:
            print "| -- --- ---- |    -- |    -- | City not found                                 |"
        print "+-------------'-------'-------'------------------------------------------------+"

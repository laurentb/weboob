# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from weboob.capabilities.housing import ICapHousing, Query
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Flatboob']


class HousingFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'cost', 'currency', 'area', 'date', 'text')

    def flush(self):
        pass

    def format_dict(self, item):
        result = u'%s%s%s\n' % (self.BOLD, item['title'], self.NC)
        result += 'ID: %s\n' % item['id']
        result += 'Cost: %s%s\n' % (item['cost'], item['currency'])
        result += u'Area: %sm²\n' % (item['area'])
        if item['date']:
            result += 'Date: %s\n' % item['date'].strftime('%Y-%m-%d')
        result += 'Phone: %s\n' % item['phone']
        if item['location']:
            result += 'Location: %s\n' % item['location']
        if item['station']:
            result += 'Station: %s\n' % item['station']

        if item['photos']:
            result += '\n%sPhotos%s\n' % (self.BOLD, self.NC)
            for photo in item['photos']:
                result += ' * %s\n' % photo.url

        result += '\n%sDescription%s\n' % (self.BOLD, self.NC)
        result += item['text']

        if item['details']:
            result += '\n\n%sDetails%s\n' % (self.BOLD, self.NC)
            for key, value in item['details'].iteritems():
                result += ' %s: %s\n' % (key, value)
        return result

class HousingListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'cost', 'text')

    count = 0

    def flush(self):
        self.count = 0
        pass

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s%s - %s (%s)%s\n' % (self.BOLD, self.count, item['cost'], item['currency'], item['title'], backend, self.NC)
        else:
            result = u'%s* (%s) %s%s - %s%s\n' % (self.BOLD, item['id'], item['cost'], item['currency'], item['title'], self.NC)
        result += '            '
        if item['date']:
            result += '%s - ' % item['date'].strftime('%Y-%m-%d')
        result += item['text']
        return result

class Flatboob(ReplApplication):
    APPNAME = 'flatboob'
    VERSION = '0.b'
    COPYRIGHT = 'Copyright(C) 2012 Romain Bignon'
    DESCRIPTION = 'Console application to search a house.'
    CAPS = ICapHousing
    EXTRA_FORMATTERS = {'housing_list': HousingListFormatter,
                        'housing':      HousingFormatter,
                       }
    COMMANDS_FORMATTERS = {'search': 'housing_list',
                           'info': 'housing',
                          }

    def main(self, argv):
        self.load_config()
        return ReplApplication.main(self, argv)

    def do_search(self, line):
        pattern = 'notempty'
        query = Query()
        query.cities = []
        while pattern:
            if len(query.cities) > 0:
                print '\n%sSelected cities:%s %s' % (self.BOLD, self.NC, ', '.join([c.name for c in query.cities]))
            pattern = self.ask('Enter a city pattern (or empty to stop)', default='')
            if not pattern:
                break

            cities = []
            for backend, city in self.do('search_city', pattern):
                cities.append(city)

            if len(cities) == 0:
                print '  Not found!'
                continue
            if len(cities) == 1:
                if city in query.cities:
                    query.cities.remove(city)
                else:
                    query.cities.append(city)
                continue

            r = 'notempty'
            while r != '':
                for i, city in enumerate(cities):
                    print '  %s%2d)%s [%s] %s' % (self.BOLD, i+1, self.NC, 'x' if city in query.cities else ' ', city.name)
                r = self.ask('  Select cities (or empty to stop)', regexp='(\d+|)', default='')
                if not r.isdigit():
                    continue
                r = int(r)
                if r <= 0 or r > len(cities):
                    continue
                city = cities[r-1]
                if city in query.cities:
                    query.cities.remove(city)
                else:
                    query.cities.append(city)

        query.area_min = self.ask_int('Enter min area')
        query.area_max = self.ask_int('Enter max area')
        query.cost_min = self.ask_int('Enter min cost')
        query.cost_max = self.ask_int('Enter max cost')

        for backend, housing in self.do('search_housings', query):
            self.add_object(housing)
            self.format(housing)
        self.flush()

    def ask_int(self, txt):
        r = self.ask(txt, default='', regexp='(\d+|)')
        if r:
            return int(r)
        return None

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        housing = self.get_object(_id, 'get_housing', [])
        if not housing:
            print >>sys.stderr, 'Housing not found: %s' %  _id
            return 3
        self.format(housing)
        self.flush()

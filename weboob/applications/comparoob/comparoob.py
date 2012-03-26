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


from __future__ import with_statement

import sys

from weboob.capabilities.pricecomparison import ICapPriceComparison
from weboob.tools.misc import html2text
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Comparoob']


class PriceFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'cost', 'currency', 'shop', 'product')

    def flush(self):
        pass

    def format_dict(self, item):
        if item['message']:
            message = item['message']
        else:
            message = '%s (%s)' % (item['shop'].name, item['shop'].location)

        result = u'%s%s%s\n' % (self.BOLD, message, self.NC)
        result += 'ID: %s\n' % item['id']
        result += 'Product: %s\n' % item['product'].name
        result += 'Cost: %s%s\n' % (item['cost'], item['currency'])
        if item['date']:
            result += 'Date: %s\n' % item['date'].strftime('%Y-%m-%d')

        result += '\n%sShop:%s\n' % (self.BOLD, self.NC)
        result += '\tName: %s\n' % item['shop'].name
        if item['shop'].location:
            result += '\tLocation: %s\n' % item['shop'].location
        if item['shop'].info:
            result += '\n\t' + html2text(item['shop'].info).replace('\n', '\n\t').strip()

        return result


class PricesFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'cost', 'currency', 'shop')

    count = 0

    def flush(self):
        self.count = 0

    def format_dict(self, item):
        self.count += 1
        if item['message']:
            message = item['message']
        else:
            message = '%s (%s)' % (item['shop'].name, item['shop'].location)

        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            result = u'%s* (%d) %s%s - %s (%s)%s' % (self.BOLD, self.count, item['cost'], item['currency'], message, backend, self.NC)
        else:
            result = u'%s* (%s) %s%s - %s%s' % (self.BOLD, item['id'], item['cost'], item['currency'], message, self.NC)
        if item['date']:
            result += ' %s' % item['date'].strftime('%Y-%m-%d')
        return result

class Comparoob(ReplApplication):
    APPNAME = 'comparoob'
    VERSION = '0.c'
    COPYRIGHT = 'Copyright(C) 2012 Romain Bignon'
    DESCRIPTION = 'Console application to compare products.'
    DEFAULT_FORMATTER = 'table'
    EXTRA_FORMATTERS = {'prices':       PricesFormatter,
                        'price':        PriceFormatter,
                       }
    COMMANDS_FORMATTERS = {'prices':    'prices',
                           'info':      'price',
                          }
    CAPS = ICapPriceComparison

    def do_prices(self, pattern):
        products = []
        for backend, product in self.do('search_products', pattern):
            products.append(product)

        if len(products) == 0:
            print >>sys.stderr, 'Error: no product found with this pattern'
            return 1
        elif len(products) == 1:
            product = products[0]
        else:
            print >>sys.stderr, 'Error: too many results, TODO'
            return 1

        self.change_path([u'prices'])
        for backend, price in self.do('iter_prices', product):
            self.add_object(price)
            self.format(price)

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        if not _id:
            print >>sys.stderr, 'This command takes an argument: %s' % self.get_command_help('info', short=True)
            return 2

        price = self.get_object(_id, 'get_price')
        if not price:
            print >>sys.stderr, 'Price not found: %s' %  _id
            return 3
        self.format(price)
        self.flush()

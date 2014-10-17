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

from __future__ import print_function

from weboob.capabilities.pricecomparison import CapPriceComparison
from weboob.tools.html import html2text
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Comparoob']


class PriceFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'cost', 'currency', 'shop', 'product')

    def format_obj(self, obj, alias):
        if hasattr(obj, 'message') and obj.message:
            message = obj.message
        else:
            message = u'%s (%s)' % (obj.shop.name, obj.shop.location)

        result = u'%s%s%s\n' % (self.BOLD, message, self.NC)
        result += u'ID: %s\n' % obj.fullid
        result += u'Product: %s\n' % obj.product.name
        result += u'Cost: %s%s\n' % (obj.cost, obj.currency)
        if hasattr(obj, 'date') and obj.date:
            result += u'Date: %s\n' % obj.date.strftime('%Y-%m-%d')

        result += u'\n%sShop:%s\n' % (self.BOLD, self.NC)
        result += u'\tName: %s\n' % obj.shop.name
        if obj.shop.location:
            result += u'\tLocation: %s\n' % obj.shop.location
        if obj.shop.info:
            result += u'\n\t' + html2text(obj.shop.info).replace('\n', '\n\t').strip()

        return result


class PricesFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'cost', 'currency')

    def get_title(self, obj):
        if hasattr(obj, 'message') and obj.message:
            message = obj.message
        elif hasattr(obj, 'shop') and obj.shop:
            message = '%s (%s)' % (obj.shop.name, obj.shop.location)
        else:
            return u'%s%s' % (obj.cost, obj.currency)

        return u'%s%s - %s' % (obj.cost, obj.currency, message)

    def get_description(self, obj):
        if obj.date:
            return obj.date.strftime('%Y-%m-%d')


class Comparoob(ReplApplication):
    APPNAME = 'comparoob'
    VERSION = '1.1'
    COPYRIGHT = 'Copyright(C) 2012-YEAR Romain Bignon'
    DESCRIPTION = "Console application to compare products."
    SHORT_DESCRIPTION = "compare products"
    DEFAULT_FORMATTER = 'table'
    EXTRA_FORMATTERS = {'prices':       PricesFormatter,
                        'price':        PriceFormatter,
                       }
    COMMANDS_FORMATTERS = {'prices':    'prices',
                           'info':      'price',
                          }
    CAPS = CapPriceComparison

    def do_prices(self, pattern):
        """
        prices [PATTERN]

        Display prices for a product. If a pattern is supplied, do not prompt
        what product to compare.
        """
        products = []
        for product in self.do('search_products', pattern):
            double = False
            for prod in products:
                if product.name == prod.name:
                    double = True
                    break
            if not double:
                products.append(product)

        product = None
        if len(products) == 0:
            print('Error: no product found with this pattern', file=self.stderr)
            return 1
        elif len(products) == 1:
            product = products[0]
        else:
            print('What product do you want to compare?')
            for i, p in enumerate(products):
                print('  %s%2d)%s %s' % (self.BOLD, i+1, self.NC, p.name))
            r = int(self.ask('  Select a product', regexp='\d+'))
            while product is None:
                if r <= 0 or r > len(products):
                    print('Error: Please enter a valid ID')
                    continue
                product = products[r-1]

        self.change_path([u'prices'])
        self.start_format()
        products = []
        for price in self.do('iter_prices', product):
            products.append(price)
        for price in sorted(products, key=self._get_price):
            self.cached_format(price)

    def _get_price(self, price):
        return price.cost

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, _id):
        """
        info ID

        Get information about a product.
        """
        if not _id:
            print('This command takes an argument: %s' % self.get_command_help('info', short=True), file=self.stderr)
            return 2

        price = self.get_object(_id, 'get_price')
        if not price:
            print('Price not found: %s' % _id, file=self.stderr)
            return 3

        self.start_format()
        self.format(price)

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


#from decimal import Decimal
#import re

from weboob.tools.browser import BasePage, BrokenPageError
from weboob.capabilities import NotAvailable
from weboob.capabilities.pricecomparison import Product, Price, Shop
import re
from decimal import Decimal

__all__ = ['MainPage','ListingAutoPage']

class MainPage(BasePage):
    def iter_products(self, criteria):
        product = Product(1)
        # TODO check if criteria exists in main page
        # and get the GET keyword to fill request ?
        product.name = unicode('Occasion')
        product._criteria = criteria
        yield product

class ListingAutoPage(BasePage):

    def _extract(self, tr, name):
        'Extract content from td element with class name'
        td = tr.cssselect('td.' + name + ' a')
        if not td:
            return ''
        return td[-1].text_content().strip()

    def iter_prices(self, product, numpage):
        for tr in self.document.getroot().cssselect('tr.lcline[id],tr.lclineJB[id],tr.lclineJ[id]'):
            id = '{numpage}.{id}'.format(numpage=numpage, id=tr.attrib['id'][3:])
            title = self._extract(tr, 'lcbrand')
            if not title:
                continue
            title += ', ' + self._extract(tr, 'lcmodel')
            ntr = tr.getnext()
            title += ', ' + self._extract(ntr, 'lcversion')
            title += ', ' + self._extract(tr, 'lcyear')
            dist = self._extract(tr, 'lcmileage') + 'km'
            title += ', ' + dist.replace(' ','')

            cost = ', ' + self._extract(tr, 'lcprice')

            price = Price(id)
            price.product = product
            price.cost = Decimal(re.findall(r'\d+',cost.replace(' ',''))[0])
            price.currency = u'€'
            price.message = unicode(title)
            price.shop = Shop(price.id)
            price.shop.set_empty_fields(NotAvailable)

            price.set_empty_fields(NotAvailable)
            yield price

    def get_next(self):
        for a in self.document.getroot().cssselect('a.page'):
            s = a.getprevious()
            if s is not None and s.tag=='span':
                m = re.search('num=(\d+)', a.get('href'))
                if not m:
                    return None
                return int(m.group(1))
        return None

#class ComparisonResultsPage(BasePage):
    #def get_product_name(self):
        #try:
            #div = self.parser.select(self.document.getroot(), 'div#moins_plus_ariane', 1)
        #except BrokenPageError:
            #return NotAvailable
        #else:
            #m = re.match('Carburant : ([\w\-]+) | .*', div.text)
            #return m.group(1)

    #def iter_results(self, product=None):
        #price = None
        #product.name = self.get_product_name()
        #for tr in self.document.getroot().cssselect('table#tab_resultat tr'):
            #if tr.attrib.get('id', '').startswith('pdv'):
                #price = Price('%s.%s' % (product.id, tr.attrib['id'][3:]))

                #price.product = product

                #tds = tr.findall('td')
                #price.cost = Decimal(tds[4].text.replace(',', '.'))
                #price.currency = u'€'

                #shop = Shop(price.id)
                #shop.name = unicode(tds[2].text.strip())
                #shop.location = unicode(tds[0].text.strip())

                #price.shop = shop
                #price.set_empty_fields(NotAvailable)
                #yield price


#class ShopInfoPage(BasePage):
    #def get_info(self):
        #return self.parser.tostring(self.parser.select(self.document.getroot(), 'div.colg', 1))

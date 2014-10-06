# -*- coding: utf-8 -*-

# Copyright(C) 2014 Vicnet
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


from decimal import Decimal
import re

from weboob.deprecated.browser import Page
from weboob.capabilities import NotAvailable, NotLoaded
from weboob.capabilities.pricecomparison import Product, Price, Shop


# I manage main page, ie do nothing yet
class MainPage(Page):
    def iter_products(self, criteria):
        product = Product(1)
        # TODO check if criteria exists in main page
        # and get the GET keyword to fill request ?
        product.name = unicode('Occasion')
        product._criteria = criteria
        yield product


def get_decimal(s):
    return re.findall(r'\d+', s.replace(' ', ''))[0]


def new_shop(id):
    shop = Shop(id)
    shop.set_empty_fields(NotLoaded)
    return shop


def new_price(id, product, cost, title):
    price = Price(id)
    price.product = product
    price.cost = Decimal(get_decimal(cost))
    price.currency = u'EUR'
    price.message = unicode(title)
    price.set_empty_fields(NotAvailable)
    price.shop = new_shop(id)
    return price


# I manage listing page and extract information
class ListingAutoPage(Page):

    def _extract(self, tr, name):
        'Extract content from td element with class name'
        td = tr.cssselect('td.' + name + ' a')
        if not td:
            return ''
        return td[-1].text_content().strip()

    def _extract_id(self, tr):
        tdas = tr.cssselect('td.lcbrand a')
        if tdas is None or len(tdas) == 0:
            return None
        tda = tdas[0]
        m = re.search('annonce-(\d+)\.html', tda.get('href'))
        if not m:
            return None
        return m.group(1)

    def iter_prices(self, product, numpage):
        for tr in self.document.getroot().cssselect('tr.lcline[id],tr.lclineJB[id],tr.lclineJ[id],tr.lclineB[id]'):
            id = self._extract_id(tr)
            title = self._extract(tr, 'lcbrand')
            if not title:
                continue
            title += ', ' + self._extract(tr, 'lcmodel')
            ntr = tr.getnext()
            title += ', ' + self._extract(ntr, 'lcversion')
            title += ', ' + self._extract(tr, 'lcyear')
            dist = self._extract(tr, 'lcmileage') + 'km'
            title += ', ' + dist.replace(' ', '')

            cost = ', ' + self._extract(tr, 'lcprice')

            yield new_price(id, product, cost, title)

    def get_next(self):
        for a in self.document.getroot().cssselect('a.page'):
            s = a.getprevious()
            if s is not None and s.tag == 'span':
                m = re.search('num=(\d+)', a.get('href'))
                if not m:
                    return None
                return int(m.group(1))
        return None


# I manage one car page (annonce) )and extract information
class AnnoncePage(Page):

    def _extract(self, e, name):
        'Extract content from li element with class name'
        li = e.cssselect('li.' + name)
        if not li:
            return ''
        return li[0].text_content().strip()

    def _extract_info(self, e, name):
        'Extract content from InfoLib'
        for td in e.cssselect('td.InfoLib'):
            if name in td.text_content():
                ntd = td.getnext()
                if ntd is None:
                    continue
                return ntd.text_content().strip()
        return None

    def _extract_vendor(self, e, name):
        'Extract content from VendorLib'
        for span in e.cssselect('span.VendeurLib'):
            if name in span.text_content():
                li = span.getparent()
                if li is None:
                    continue
                # get all text
                s = li.text_content()
                # get text without header
                s = s[len(span.text_content())+1:]
                # special case for not pro
                if '\n' in s:
                    s = s[:s.find('\n')]
                return s.strip()
        return None

    def get_shop(self, id):
        shop = Shop(id)
        for e in self.document.getroot().cssselect('div#Vendeur'):
            shop.name = self._extract_vendor(e, 'Nom') + '(' + self._extract_vendor(e, 'Vendeur') + ')'
        shop.location = ''
        for adr in self.document.getroot().cssselect('span#AdresseL1,span#AdresseL2'):
            if shop.location:
                shop.location += ', '
            shop.location += adr.text_content().strip()
        for tel in self.document.getroot().cssselect('span.Tel'):
            s = tel.text_content().strip()
            if shop.location:
                shop.location += ', '
            shop.location += re.sub('\s+', ' ', s)
        shop.set_empty_fields(NotAvailable)
        return shop

    def get_price(self, id):
        for e in self.document.getroot().cssselect('div#DescBar'):
            product = Product(1)
            product.name = unicode('Occasion')
            cost = self._extract(e, 'PriceLc')
            title = self._extract(e, 'BrandLc')
            title += ', ' + self._extract(e, 'modeleCom')
            title += ', ' + self._extract_info(e, 'Version')
            title += ', ' + self._extract_info(e, 'Ann')
            title += ', ' + get_decimal(self._extract_info(e, 'Kilom')) + 'km'
            price = new_price(id, product, cost, title)
            price.shop = self.get_shop(id)
            return price

# -*- coding: utf-8 -*-

# Copyright(C) 2015      Oleg Plakhotniuk
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


from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.pages import HTMLPage
from weboob.capabilities.base import Currency
from weboob.capabilities.shop import Order, Item, Payment, OrderNotFound
from weboob.exceptions import BrowserIncorrectPassword

import re
from decimal import Decimal
from datetime import datetime
from itertools import takewhile, count


__all__ = ['Ideel']


class IdeelPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath('//a[@href="/logout"]'))


class LoginPage(IdeelPage):
    def login(self, username, password):
        form = self.get_form(xpath='//form[@id="iform"]')
        form['login'] = username
        form['password'] = password
        form.submit()


class HistoryPage(IdeelPage):
    def exists(self):
        return bool(self.doc.xpath('//table[@id="order_history"]'))

    def iter_orders(self):
        return (tr.xpath('td[1]/a/text()')[0][1:]
          for tr in self.doc.xpath('//table[@id="order_history"]/tbody/tr'))


class OrderPage(IdeelPage):
    def exists(self):
        return bool(self.order_number())

    def order(self):
        order = Order(id=self.order_number())
        order.date = self.order_date()
        order.tax = self.tax()
        order.shipping = self.shipping()
        order.discount = self.discount()
        order.total = self.total()
        return order

    def items(self):
        for tr in self.doc.xpath('//table[contains(@class,"items_table")]'
                                 '/tr[td[@class="items_desc"]]'):
            label = tr.xpath('*//div[@class="item_desc"]//span/text()')[0]
            url = tr.xpath('*//div[@class="item_img"]//@src')[0]
            onclk = tr.xpath('*//div[@class="item_img"]//@onclick')
            if onclk:
                url=re.match(r'window.open\(\'([^\']*)\'.*', onclk[0]).group(1)
            if url.startswith('/'):
                url = self.browser.BASEURL + url
            price = tr.xpath('td[@class="items_price"]/span/text()')[0]
            qty = tr.xpath('td[@class="items_qty"]//span/text()')[0]
            price = AmTr.decimal_amount(price) * Decimal(qty)
            item = Item()
            item.label = unicode(label)
            item.url = unicode(url)
            item.price = price
            yield item

    def payments(self):
        # There's no payment information on Ideel, so we'll make one up.
        p = Payment()
        p.date = self.order_date()
        p.method = u'DEFAULT PAYMENT'
        p.amount = self.total()
        yield p

    def order_number(self):
        return next(iter(self.doc.xpath(
            u'//b[text()="Order Number:"]/../strong/text()')), None)

    def order_date(self):
        txt = self.doc.xpath('//div[@id="purchase-notice"]/text()')[0]
        date = re.match(r'.* (\w+ \d+, \d+)$', txt).group(1)
        return datetime.strptime(date, '%b %d, %Y')

    def tax(self):
        return AmTr.decimal_amount(self.doc.xpath(
            '//span[@id="taxes"]/text()')[0])

    def shipping(self):
        return AmTr.decimal_amount(self.doc.xpath(
            '//span[@id="shipping_fee"]/text()')[0])

    def discount(self):
        TAGS = ['coupon_discount_amount', 'promo_discount_amount',
                'total_rewards', 'applied_credit']
        return -sum(AmTr.decimal_amount(x[1:][:-1]) for tag in TAGS
            for x in self.doc.xpath('//span[@id="%s"]/text()' % tag))

    def total(self):
        return AmTr.decimal_amount(self.doc.xpath(
            '//span[@id="total"]/text()')[0])


class Ideel(LoginBrowser):
    BASEURL = 'http://www.ideel.com'
    login = URL(r'https://www.ideel.com/login$', LoginPage)
    history = URL(r'/my_account/orders\?page=(?P<page>\d+)$', HistoryPage)
    order = URL(r'/my_account/orders/(?P<order>\d+)$', OrderPage)
    unknown = URL(r'/.*$', IdeelPage)

    def get_currency(self):
        # Ideel uses only U.S. dollars.
        return Currency.get_currency(u'$')

    @need_login
    def get_order(self, id_):
        if self.order.go(order=id_).exists():
            return self.page.order()
        raise OrderNotFound()

    @need_login
    def iter_orders(self):
        exists = HistoryPage.exists
        hists = takewhile(exists, (self.history.go(page=i) for i in count(1)))
        return (self.get_order(x) for h in hists for x in h.iter_orders())

    @need_login
    def iter_payments(self, order):
        return self.order.stay_or_go(order=order.id).payments()

    @need_login
    def iter_items(self, order):
        return self.order.stay_or_go(order=order.id).items()

    def do_login(self):
        self.login.stay_or_go().login(self.username, self.password)
        if not self.page.logged:
            raise BrowserIncorrectPassword()

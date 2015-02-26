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


from requests.exceptions import Timeout

from weboob.tools.capabilities.bank.transactions import \
    AmericanTransaction as AmTr
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.pages import HTMLPage
from weboob.capabilities.base import Currency
from weboob.capabilities.shop import OrderNotFound, Order, Payment, Item
from weboob.exceptions import BrowserIncorrectPassword

from datetime import datetime
from decimal import Decimal


__all__ = ['MyHabit']


class MyHabitPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath('//a[text()="Sign Out"]'))


class LoginPage(MyHabitPage):
    def login(self, username, password):
        form = self.get_form(name='signIn')
        form['email'] = username
        form['password'] = password
        form.submit()
        return self.browser.page


class HistoryPage(MyHabitPage):
    def to_year(self, year):
        form = self.get_form(xpath='//form[@id="viewOrdersHistory"]')
        form['orderRange'] = year
        form.submit()
        return self.browser.page

    def years(self):
        return self.doc.xpath('//option[contains(@value,"FULL_YEAR")]/@value')

    def iter_orders(self):
        return self.doc.xpath('//a[contains(@href,"ViewOrdersDetail")]/@href')


class OrderPage(MyHabitPage):
    def order(self, url):
        order = Order(id=self.order_number())
        order._url = url
        order.date = self.order_date()
        order.tax = self.tax()
        order.shipping = self.shipping()
        order.discount = self.discount()
        order.total = self.total()
        return order

    def payments(self):
        method = self.doc.xpath('//div[@class="creditCard"]/text()')[0].strip()
        pmt = Payment()
        pmt.date = self.order_date()
        pmt.method = unicode(method)
        pmt.amount = self.total()
        yield pmt

    def items(self):
        for span in self.doc.xpath('//div[@class="shipmentItems1"]'
                                   '/span[@class="item"]'):
            url = span.xpath('span[@class="itemLink"]/a/@href')[0]
            label = span.xpath('span[@class="itemLink"]/a/text()')[0]
            qty = span.xpath('span[@class="itemQuantity"]/text()')[0]
            price = span.xpath('span[@class="itemPrice"]/text()')[0]
            price = Decimal(qty)*AmTr.decimal_amount(price)
            item = Item()
            item.url = unicode(url)
            item.label = unicode(label)
            item.price = price
            yield item

    def order_date(self):
        date = self.doc.xpath(u'//span[text()="Order Placed:"]'
                               '/following-sibling::span[1]/text()')[0].strip()
        return datetime.strptime(date, '%b %d, %Y')

    def order_number(self):
        return self.doc.xpath(u'//span[text()="MYHABIT Order Number:"]'
                               '/following-sibling::span[1]/text()')[0].strip()

    def order_amount(self, which):
        return AmTr.decimal_amount((self.doc.xpath(
            '//tr[@class="%s"]/td[2]/text()' % which) or ['0'])[0])

    def tax(self):
        return self.order_amount('tax')

    def shipping(self):
        return self.order_amount('shippingCharge')

    def discount(self):
        TAGS = ['discount', 'gc']
        return sum(self.order_amount(t) for t in TAGS)

    def total(self):
        return self.order_amount('total')


class MyHabit(LoginBrowser):
    BASEURL = 'https://www.myhabit.com'
    MAX_RETRIES = 10
    login = URL(r'/signin', r'https://www.amazon.com/ap/signin.*$', LoginPage)
    order = URL(r'/vieworders\?.*appAction=ViewOrdersDetail.*', OrderPage)
    history = URL(r'/vieworders$',
                  r'/vieworders\?.*appAction=ViewOrdersHistory.*', HistoryPage)
    unknown = URL(r'/.*$', r'http://www.myhabit.com/.*$', MyHabitPage)

    def get_currency(self):
        # MyHabit uses only U.S. dollars.
        return Currency.get_currency(u'$')

    @need_login
    def get_order(self, id_):
        # MyHabit requires dynamically generated token each time you
        # request order details, which makes it problematic to get an order
        # by id. Hence this slow and painful stub.
        for year in self.history.stay_or_go().years():
            hist = self.history.stay_or_go().to_year(year)
            for url in hist.iter_orders():
                if id_ in url:
                    self.location(url)
                    assert self.order.is_here()
                    o = self.page.order(url)
                    if o.id == id_:
                        return o
        raise OrderNotFound()

    @need_login
    def iter_orders(self):
        for year in self.history.stay_or_go().years():
            hist = self.history.stay_or_go().to_year(year)
            for url in hist.iter_orders():
                self.location(url)
                assert self.order.is_here()
                yield self.page.order(url)

    @need_login
    def iter_payments(self, order):
        if self.url != self.BASEURL+order._url:
            self.location(order._url)
        assert self.order.is_here()
        return self.page.payments()

    @need_login
    def iter_items(self, order):
        if self.url != self.BASEURL+order._url:
            self.location(order._url)
        assert self.order.is_here()
        return self.page.items()

    def do_login(self):
        if not self.login.go().login(self.username, self.password).logged:
            raise BrowserIncorrectPassword()

    def location(self, *args, **kwargs):
        for i in xrange(self.MAX_RETRIES):
            try:
                return super(MyHabit, self).location(*args, **kwargs)
            except Timeout as e:
                pass
        raise e

# -*- coding: utf-8 -*-

# Copyright(C) 2014      Oleg Plakhotniuk
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
from weboob.capabilities.shop import Order, Payment, Item
from weboob.browser.pages import HTMLPage, pagination, NextPage

from datetime import datetime
from decimal import Decimal
import re


class AmazonPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//*[contains(text(),"Sign Out")]'))


class HomePage(AmazonPage):
    def to_login(self):
        url1 = self.doc.xpath('//a[@id="nav-link-yourAccount"]/@href')
        url2 = self.doc.xpath('//a[@id="nav-your-account"]/@href')
        self.browser.location((url1 or url2)[0])
        return self.browser.page


class LoginPage(AmazonPage):
    def login(self, email, password):
        form = self.get_form(name='signIn')
        form['email'] = email
        form['password'] = password
        form.submit()


class HistoryPage(AmazonPage):
    def iter_years(self):
        for year in self.opt_years():
            yield self.to_year(year)

    @pagination
    def iter_orders(self):
        for id_ in self.doc.xpath(
                u'//span[contains(text(),"Order #")]/../span[2]/text()'):
            yield self.browser.to_order(id_.strip())
        for next_ in self.doc.xpath(u'//ul[@class="a-pagination"]'
                                    u'//a[contains(text(),"Next")]/@href'):
            raise NextPage(next_)

    def to_year(self, year):
        form = self.get_form('//form[contains(@class,"time-period-chooser")]')
        form['orderFilter'] = [year]
        form.submit()
        return self.browser.page

    def opt_years(self):
        return [x for x in self.doc.xpath(
            '//select[@name="orderFilter"]/option/@value'
            ) if x.startswith('year-')]


class OrderPage(AmazonPage):
    def shouldSkip(self):
        # Reports only fully shipped and delivered orders, because they have
        # finalized payment amounts.
        # Payment for not yet shipped orders may change, and is not always
        # available.
        return bool([x for s in [u'Not Yet Shipped', u'Not yet shipped',
                                 u'Preparing for Shipment', u'Shipping now', u'In transit',
                                 u'On the way']
                    for x in self.doc.xpath(u'//*[contains(text(),"%s")]' % s)])


class OrderNewPage(OrderPage):
    is_here = u'//*[contains(text(),"Ordered on")]'

    def order(self):
        if not self.shouldSkip():
            order = Order(id=self.order_number())
            order.date = self.order_date()
            order.tax = self.tax()
            order.discount = self.discount()
            order.shipping = self.shipping()
            return order

    def order_date(self):
        return datetime.strptime(
            re.match('.*Ordered on ([^ ]+ [0-9]+, [0-9]+) .*',
                     self.date_num()).group(1),
            '%B %d, %Y')

    def order_number(self):
        m = re.match('.*Order# +([^ ]+) .*', self.date_num())
        if m:
            return m.group(1)

    def payments(self):
        if self.gift():
            pmt = Payment()
            pmt.date = self.order_date()
            pmt.method = u'GIFT CARD'
            pmt.amount = -self.gift()
            yield pmt
        transactions = list(self.transactions())
        if transactions:
            for t in transactions:
                yield t
        else:
            for method in self.paymethods():
                pmt = Payment()
                pmt.date = self.order_date()
                pmt.method = method
                pmt.amount = self.grand_total()
                yield pmt
                break

    def paymethods(self):
        for root in self.doc.xpath('//h5[contains(text(),"Payment Method")]'):
            alt = root.xpath('../div/img/@alt')[0]
            span = root.xpath('../div/span/text()')[0]
            digits = re.match(r'[^0-9]*([0-9]+)[^0-9]*', span).group(1)
            yield u'%s %s' % (alt, digits)

    def grand_total(self):
        return AmTr.decimal_amount(self.doc.xpath(
            u'//span[contains(text(),"Grand Total:")]/..'
            u'/following-sibling::div[1]/span/text()')[0].strip())

    def date_num(self):
        return u' '.join(self.doc.xpath(
            '//span[@class="order-date-invoice-item"]/text()'
            ) or self.doc.xpath(
            '//*[contains(text(),"Ordered on")]/text()')).replace('\n', '')

    def tax(self):
        return self.amount(u'Estimated tax to be collected')

    def shipping(self):
        return self.amount(u'Free shipping', u'Free Shipping',
                           u'Shipping & Handling')

    def discount(self):
        return self.amount(u'Promotion applied', u'Promotion Applied',
                           u'Subscribe & Save', u'Your Coupon Savings',
                           u'Lightning Deal')

    def gift(self):
        return self.amount(u'Gift Card Amount')

    def amount(self, *names):
        return Decimal(sum(AmTr.decimal_amount(amount.strip())
                       for n in names for amount in self.doc.xpath(
                       '(//span[contains(text(),"%s:")]/../..//span)[2]/text()' % n)))

    def transactions(self):
        for row in self.doc.xpath('//span[contains(text(),"Transactions")]'
                                  '/../../div/div'):
            text = row.text_content().strip().replace('\n', ' ')
            if u'Items shipped:' not in text:
                continue
            date, method, amount = re.match(
                '.* '     '([A-z]+ [0-9]+, [0-9]+)'
                '[ -]+'   '([A-z][^:]+)'
                ': +'     '([^ ]+)', text).groups()
            date = datetime.strptime(date, '%B %d, %Y')
            method = method.replace(u'ending in ', u'').upper()
            amount = AmTr.decimal_amount(amount)
            pmt = Payment()
            pmt.date = date
            pmt.method = method
            pmt.amount = amount
            yield pmt

    def items(self):
        for item in self.doc.xpath('//div[contains(@class,"a-box shipment")]'
                                   '/div/div/div/div/div/div'):
            url = (item.xpath(u'*//a[contains(@href,"/gp/product")]/@href') +
                   [u''])[0]
            label = u''.join(item.xpath(
                '*//a[contains(@href,"/gp/product")]/text()')).strip()
            price = u''.join(x.strip() for x in item.xpath(
                '*//span[contains(text(),"$")]/text()')
                if x.strip().startswith('$'))
            price = AmTr.decimal_amount(price)
            multi = re.match(u'([0-9]+) of (.*)', label)
            if multi:
                amount, label = multi.groups()
                price *= Decimal(amount)
            if url:
                url = unicode(self.browser.BASEURL) + \
                    re.match(u'(/gp/product/.*)/ref=.*', url).group(1)
            if label and price:
                itm = Item()
                itm.label = label
                itm.url = url
                itm.price = price
                yield itm


class OrderOldPage(OrderPage):
    is_here = u'//*[contains(text(),"Amazon.com order number")]'

    def order(self):
        if not self.shouldSkip():
            order = Order(id=self.order_number())
            order.date = self.order_date()
            order.tax = self.tax()
            order.discount = self.discount()
            order.shipping = self.shipping()
            return order

    def order_date(self):
        return datetime.strptime(u' '.join(self.doc.xpath(
            u'//b[contains(text(),"Order Placed")]/../text()')).strip(),
            '%B %d, %Y')

    def order_number(self):
        return u' '.join(self.doc.xpath(
            u'//td/b[contains(text(),"Amazon.com order number")]/../text()')
        ).strip()

    def tax(self):
        return self.sum_amounts(u'Sales Tax:')

    def discount(self):
        return self.sum_amounts(u'Subscribe & Save:', u'Promotion applied:',
                                u'Promotion Applied:', u'Your Coupon Savings:')

    def shipping(self):
        return self.sum_amounts(u'Shipping & Handling:', u'Free shipping:',
                                u'Free Shipping:')

    def payments(self):
        for shmt in self.shipments():
            gift = self.gift(shmt)
            if gift:
                pmt = Payment()
                pmt.date = self.order_date()
                pmt.method = u'GIFT CARD'
                pmt.amount = -gift
                yield pmt
        transactions = list(self.transactions())
        if transactions:
            for t in transactions:
                yield t
        else:
            for method in self.paymethods():
                pmt = Payment()
                pmt.date = self.order_date()
                pmt.method = method
                pmt.amount = self.grand_total()
                yield pmt
                break

    def shipments(self):
        for cue in (u'Shipment #', u'Subscribe and Save Shipment'):
            for shmt in self.doc.xpath('//b[contains(text(),"%s")]' % cue):
                yield shmt

    def items(self):
        for shmt in self.shipments():
            root = shmt.xpath(u'../../../../../../../..'
                              u'//b[text()="Items Ordered"]')[0]
            for item in root.xpath('../../../tr')[1:]:
                count = url = label = None
                for div in item.xpath('*//div'):
                    m = re.match(u'^\s*(\d+)\s*of:(.*)$', div.text,
                                 re.MULTILINE + re.DOTALL)
                    if not m:
                        continue
                    count = Decimal(m.group(1).strip())
                    label = unicode(m.group(2).strip())
                    if label:
                        url = u''
                    else:
                        a = div.xpath('*//a[contains(@href,"/gp/product")]')[0]
                        url = unicode(a.attrib['href'])
                        label = unicode(a.text.strip())
                price1 = item.xpath('*//div')[-1].text.strip()
                price = count * AmTr.decimal_amount(price1)

                itm = Item()
                itm.label = label
                itm.url = url
                itm.price = price
                yield itm

    def sum_amounts(self, *names):
        return sum(self.amount(shmt, x) for shmt in self.shipments()
                   for x in names)

    def amount(self, shmt, name):
        for root in shmt.xpath(u'../../../../../../../..'
                               u'//td[text()="Item(s) Subtotal: "]/../..'):
            for node in root.xpath(u'tr/td[text()="%s"]' % name):
                return AmTr.decimal_amount(
                    node.xpath('../td')[-1].text.strip())
            for node in root.xpath(u'tr/td/b[text()="%s"]' % name):
                return AmTr.decimal_amount(
                    node.xpath('../../td/b')[-1].text.strip())
        return Decimal(0)

    def gift(self, shmt):
        return self.amount(shmt, u'Gift Card Amount:')

    def paymethods(self):
        root = self.doc.xpath('//b[text()="Payment Method: "]/..')[0]
        text = root.text_content().strip()
        while text:
            for pattern in [
                    u'^.*Payment Method:',
                    u'^([^\n]+)\n +\| Last digits: +([0-9]+)\n',
                    u'^Gift Card\n',  # Skip gift card.
                    u'^Billing address.*$']:
                match = re.match(pattern, text, re.DOTALL+re.MULTILINE)
                if match:
                    text = text[match.end():].strip()
                    if match.groups():
                        yield u' '.join(match.groups()).upper()
                    break
            else:
                break

    def transactions(self):
        for tr in self.doc.xpath(
                u'//div[contains(b,"Credit Card transactions")]'
                u'/following-sibling::table[1]/tr'):
            label, date = tr.xpath('td[1]/text()')[0].strip().split(u'\xa0')
            amount = tr.xpath('td[2]/text()')[0].strip()
            date = datetime.strptime(date, '%B %d, %Y:')
            method = label.replace(u'ending in ', u'')[:-1].upper()
            amount = AmTr.decimal_amount(amount)
            pmt = Payment()
            pmt.date = date
            pmt.method = method
            pmt.amount = amount
            yield pmt

    def grand_total(self):
        return AmTr.decimal_amount(self.doc.xpath(
            '//td[b="Grand Total:"]/following-sibling::td[1]/b')[0].text)

# -*- coding: utf-8 -*-

# Copyright(C) 2015      Christophe Lampin
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

from weboob.capabilities.shop import Order, Payment, Item
from weboob.browser.pages import HTMLPage, pagination, NextPage
from weboob.capabilities.base import empty

from datetime import datetime
from decimal import Decimal
import re

# Ugly array to avoid the use of french locale
FRENCH_MONTHS = [u'janvier', u'février', u'mars', u'avril', u'mai', u'juin', u'juillet', u'août', u'septembre', u'octobre', u'novembre', u'décembre']


class AmazonPage(HTMLPage):
    @property
    def logged(self):
        return bool(self.doc.xpath(u'//*[contains(text(),"Déconnectez-vous")]'))


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
    forced_encoding = True
    ENCODING = 'UTF-8'

    def iter_years(self):
        for year in self.opt_years():
            yield self.to_year(year)

    @pagination
    def iter_orders(self):
        for id_ in self.doc.xpath(u'//span[contains(text(),"N° de commande")]/../span[2]/text()'):
            yield self.browser.to_order(id_.strip())
        for next_ in self.doc.xpath(u'//ul[@class="a-pagination"]'
                                    u'//a[contains(text(),"Suivante")]/@href'):
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

        return bool([x for s in [u'En préparation pour expédition']  # TODO : Other French status applied ?
                    for x in self.doc.xpath(u'//*[contains(text(),"%s")]' % s)])

    def decimal_amount(self, amount):
        m = re.match(u'.*EUR ([,0-9]+).*', amount)
        if m:
            return Decimal(m.group(1).replace(",", "."))

    def month_to_int(self, text):
        for (idx, month) in enumerate(FRENCH_MONTHS):
            text = text.replace(month, str(idx + 1))
        return text


class OrderNewPage(OrderPage):
    # Need to force encoding because of mixed encoding
    forced_encoding = True
    ENCODING = 'ISO-8859-15'
    is_here = u'//*[contains(text(),"Commandé le")]'

    def order(self):
        if not self.shouldSkip():
            order = Order(id=self.order_number())
            order.date = self.order_date()
            order.tax = self.tax()
            order.discount = self.discount()
            order.shipping = self.shipping()
            order.total = self.grand_total()
            return order

    def order_date(self):
        return datetime.strptime(
            re.match(u'.*Commandé le ([0-9]+ [0-9]+ [0-9]+) .*',
                     self.month_to_int(self.date_num())).group(1),
            '%d %m %Y')

    def order_number(self):
        m = re.match(u'.*N° de commande : +([^ ]+) .*', self.date_num())
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
        for root in self.doc.xpath(u'//h5[contains(text(),"Méthode de paiement")]'):
            alt = root.xpath('../div/img/@alt')[0]
            span = root.xpath('../div/span/text()')[0]
            digits = re.match(r'[^0-9]*([0-9]+)[^0-9]*', span).group(1)
            yield u'%s %s' % (alt, digits)

    def grand_total(self):
        return self.decimal_amount(self.doc.xpath(
            '//span[contains(text(),"Montant total TTC")]/..'
            '/following-sibling::div[1]/span/text()')[0].strip())

    def date_num(self):
        return u' '.join(
            self.doc.xpath(
                '//span[@class="order-date-invoice-item"]/text()'
            )).replace('\n', '')

    def tax(self):
        return self.amount(u' TVA')

    def shipping(self):
        return self.amount(u'Livraison :')

    def discount(self):
        # TODO : French translation
        return self.amount(u'Bon de réduction', u'Subscribe & Save', u'Your Coupon Savings',
                           u'Lightning Deal')

    def gift(self):
        # TODO : French translation
        return self.amount(u'Gift Card Amount')

    def amount(self, *names):
        return Decimal(sum(self.decimal_amount(amount.strip())
                       for n in names for amount in self.doc.xpath(
                       '(//span[contains(text(),"%s")]/../..//span)[2]/text()' % n)))

    def transactions(self):
        for row in self.doc.xpath('//span[contains(text(),"Transactions")]'
                                  '/../../div/div'):
            text = row.text_content().strip().replace('\n', ' ')
            if u'Expédition' not in text:
                continue
            date, method, amount = re.match(
                '.* '     '([0-9]+ [^ ]+ [0-9]+)'
                '[ -]+'   '([A-z][^:]+)'
                ': +'     '(EUR [^ ]+)', text).groups()
            date = datetime.strptime(self.month_to_int(date), '%d %m %Y')
            method = method.replace(u'finissant par ', u'').upper()
            amount = self.decimal_amount(amount)
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
                '*//span[contains(text(),"EUR")]/text()')
                if x.strip().startswith('EUR'))
            price = self.decimal_amount(price)
            multi = re.match(u'([0-9]+) de (.*)', label)
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
    forced_encoding = True
    ENCODING = 'ISO-8859-15'
    is_here = u'//*[contains(text(),"Amazon.fr numéro de commande")]'

    def order(self):
        if not self.shouldSkip():
            order = Order(id=self.order_number())
            order.date = self.order_date()
            order.tax = Decimal(self.tax()) if not empty(self.tax()) else Decimal(0.00)
            order.discount = Decimal(self.discount()) if not empty(self.discount()) else Decimal(0.00)
            order.shipping = Decimal(self.shipping()) if not empty(self.shipping()) else Decimal(0.00)
            order.total = Decimal(self.grand_total()) if not empty(self.grand_total()) else Decimal(0.00)
            return order

    def order_date(self):
        date_str = self.doc.xpath(u'//b[contains(text(),"Commande numérique")]')[0].text
        month_str = re.match(u'.*Commande numérique : [0-9]+ ([^ ]+) [0-9]+.*', date_str).group(1)
        return datetime.strptime(
            re.match(u'.*Commande numérique : ([0-9]+ [0-9]+ [0-9]+).*',
                     date_str.replace(month_str, str(FRENCH_MONTHS.index(month_str) + 1))).group(1),
            '%d %m %Y')

    def order_number(self):
        num_com = u' '.join(self.doc.xpath(
            u'//b[contains(text(),"Amazon.fr numéro de commande")]/../text()')
        ).strip()
        return num_com

    def tax(self):
        return self.sum_amounts(u'TVA:')

    def discount(self):
        # TODO : French translation
        return self.sum_amounts(u'Subscribe & Save:', u'Bon de réduction:',
                                u'Promotion Applied:', u'Your Coupon Savings:')

    def shipping(self):
        # TODO : French translation
        return self.sum_amounts(u'Shipping & Handling:', u'Free shipping:',
                                u'Free Shipping:')

    def payments(self):
        for shmt in self.shipments():
            gift = self.gift(shmt)
            if gift:
                pmt = Payment()
                pmt.date = self.order_date()
                pmt.method = u'CARTE CADEAU'
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
        # TODO : French translation
        for cue in (u'Shipment #', u'Subscribe and Save Shipment'):
            for shmt in self.doc.xpath('//b[contains(text(),"%s")]' % cue):
                yield shmt

    def items(self):
        for shmt in self.shipments():
            root = shmt.xpath(u'../../../../../../../..'
                              u'//b[text()="Articles commandés"]')[0]
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
                price = count * self.decimal_amount(price1)

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
                               u'//td[text()="Sous-total articles: "]/../..'):
            for node in root.xpath(u'tr/td[text()="%s"]' % name):
                return self.decimal_amount(
                    node.xpath('../td')[-1].text.strip())
            for node in root.xpath(u'tr/td/b[text()="%s"]' % name):
                return self.decimal_amount(
                    node.xpath('../../td/b')[-1].text.strip())
        return Decimal(0)

    def gift(self, shmt):
        # TODO : French translation
        return self.amount(shmt, u'Gift Card Amount:')

    def paymethods(self):
        # TODO : French translation
        root = self.doc.xpath('//b[text()="Payment Method: "]/..')
        if len(root) == 0:
            return
        root = root[0]
        text = root.text_content().strip()
        while text:
            # TODO : French translation
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
        # TODO : French translation
        for tr in self.doc.xpath(
                u'//div[contains(b,"Credit Card transactions")]'
                u'/following-sibling::table[1]/tr'):
            label, date = tr.xpath('td[1]/text()')[0].strip().split(u'\xa0')
            amount = tr.xpath('td[2]/text()')[0].strip()
            date = datetime.strptime(date, '%B %d, %Y:')
            method = label.replace(u'ending in ', u'')[:-1].upper()
            amount = self.decimal_amount(amount)
            pmt = Payment()
            pmt.date = date
            pmt.method = method
            pmt.amount = amount
            yield pmt

    def grand_total(self):
        return self.decimal_amount(self.doc.xpath(
            u'//td[contains(b,"Total pour cette commande")]')[0].text)

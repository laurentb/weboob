# -*- coding: utf-8 -*-

# Copyright(C) 2009-2013  Romain Bignon
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


import re
from urlparse import urlparse, parse_qsl
from decimal import Decimal, InvalidOperation

from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page

from .perso.transactions import Transaction


class ProAccountsList(Page):
    COL_LABEL   = 1
    COL_ID      = 2
    COL_BALANCE = 3
    COL_COMING  = 5

    def get_list(self, pro=True):
        accounts = []
        for tr in self.document.xpath('//tr[@class="comptes"]'):
            cols = tr.findall('td')

            if len(cols) < 5:
                continue

            account = Account()
            account.id = self.parser.tocleanstring(cols[self.COL_ID]).replace(" ", "")
            account.label = self.parser.tocleanstring(cols[self.COL_LABEL])
            account.balance = Decimal(self.parser.tocleanstring(cols[self.COL_BALANCE]))
            try:
                account.coming = Decimal(self.parser.tocleanstring(cols[self.COL_COMING]))
            except InvalidOperation:
                if self.parser.tocleanstring(cols[self.COL_COMING]) != '-':
                    self.logger.warning('Unable to parse coming value', exc_info=True)
                account.coming = NotAvailable
            account._link_id = None
            account._stp = None

            a = cols[self.COL_LABEL].find('a')
            if a is not None:
                url = urlparse(a.attrib['href'])
                p = dict(parse_qsl(url.query))
                account._link_id = p.get('ch4', None)
                account._stp = p.get('stp', None)

            for input_tag in tr.xpath('.//input[starts-with(@id, "urlRib")]'):
                m = re.search('ch4=(\w+)', input_tag.get('value', ''))
                if m:
                    account.iban = unicode(m.group(1))

            accounts.append(account)

        # If there are also personnal accounts linked, display the page and iter on them.
        if pro and len(self.document.xpath('//div[@class="onglets"]//a[contains(@href, "afficherComptesPrives")]')) > 0:
            self.browser.select_form(name='myForm')
            self.browser.set_all_readonly(False)
            self.browser['udcAction'] = '/afficherComptesPrives'
            self.browser.submit()

            for a in self.browser.page.get_list(False):
                accounts.append(a)

        return accounts


class ProAccountHistory(Page):
    COL_DATE = 0
    COL_LABEL = 1
    COL_DEBIT = -2
    COL_CREDIT = -1

    def on_loaded(self):
        # If transactions are ordered by type, force order by date.
        try:
            checkbox = self.document.xpath('//input[@name="szTriDate"]')[0]
        except IndexError:
            return

        if not 'checked' in checkbox.attrib:
            self.browser.select_form(name='formtri')
            self.browser['szTriDate'] = ['date']
            self.browser['szTriRub'] = []
            self.browser.submit()

    def iter_operations(self):
        for i, tr in enumerate(self.document.xpath('//tr[@class="hdoc1" or @class="hdotc1"]')):
            cols = tr.findall('td')

            if len(cols) < 4:
                continue

            op = Transaction(i)

            date = self.parser.tocleanstring(cols[self.COL_DATE])
            raw = self.parser.tocleanstring(cols[self.COL_LABEL])
            raw = re.sub(r'[ \xa0]+', ' ', raw).strip()
            op.parse(date=date, raw=raw)

            debit = self.parser.tocleanstring(cols[self.COL_DEBIT])
            credit = self.parser.tocleanstring(cols[self.COL_CREDIT])
            op.set_amount(credit, debit)

            yield op

    def iter_coming_operations(self):
        for i, tr in enumerate(self.document.xpath('//tr[@class="hdoc1" or @class="hdotc1"]')):
            cols = tr.findall('td')

            if len(cols) < 4:
                continue

            op = Transaction(i)

            date = self.parser.tocleanstring(cols[self.COL_DATE])
            raw = self.parser.tocleanstring(cols[self.COL_LABEL])
            raw = re.sub(r'[ \xa0]+', ' ', raw).strip()
            op.parse(date=date, raw=raw)

            credit = self.parser.tocleanstring(cols[self.COL_CREDIT])
            op.set_amount(credit)

            yield op

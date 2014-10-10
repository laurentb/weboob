# -*- coding: utf-8 -*-

# Copyright(C) 2013      Noe Rubinstein
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

from weboob.capabilities.bank import Account
from weboob.deprecated.browser import Page
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class LoginPage(Page):
    def login(self, username, password):
        self.browser.select_form(name="frmLogin")
        self.browser['username'] = username.encode('utf-8')
        self.browser['password'] = password.encode('utf-8')
        self.browser.find_control('lang').readonly = False
        self.browser['lang'] = 'fr'
        self.browser.submit(nologin=True)


class DashboardPage(Page):
    def iter_accounts(self):
        for line in self._accounts():
            yield self._get_account(line)

    def get_account(self, _id):
        xpath = './/a[@href="tbord.do?id=%s"]' % _id
        account = next(a for a in self._accounts() if a.xpath(xpath))
        return self._get_account(account)

    def _accounts(self):
        return self.document.getroot().cssselect('.tbord_account')

    _FIELD_XPATH = './/span[@class="%s"]//text()'
    _URL_XPATH = './/span[@class="accountLabel"]//a/@href'

    def _get_account(self, line):
        def get_field(field):
            return unicode(line.xpath(self._FIELD_XPATH % field)[0]).strip()

        account = Account()
        account._url = unicode(line.xpath(self._URL_XPATH)[0])
        account.id = account._url.replace("tbord.do?id=", "")
        account.balance = Decimal(FrenchTransaction.clean_amount(
            get_field('accountTotal')))
        account.label = get_field('accountLabel2')
        account.currency = account.get_currency(get_field('accountDev'))

        return account


class OperationsPage(Page):
    _LINE_XPATH = '//tr[starts-with(@class,"PL_LIGLST_")]'
    _NEXT_XPATH = '//a[contains(@class,"pg_next")]/@href'

    def iter_history(self):
        i = 0
        for line in self.document.xpath(self._LINE_XPATH):
            i += 1
            operation = Transaction(i)

            date = line.xpath('.//td[@class="nlb d"]')[0].text_content().strip()
            raw = self.parser.tocleanstring(line.xpath('.//td[@class="t"]')[0])

            amounts = line.xpath('.//td[@class="n"]')
            [debit, credit] = [amount.text_content().strip()
                               for amount in amounts]

            operation.parse(date=date, raw=raw)
            operation.set_amount(credit, debit)

            yield operation

    def next_page(self):
        next_button = self.document.xpath(self._NEXT_XPATH)
        if next_button:
            return next_button[0]


class LCRPage(OperationsPage):
    def iter_history(self):
        date = None
        for line in self.document.xpath('//table[@id="encoursTable"]/tbody/tr'):
            if line.attrib.get('class', '').startswith('PL_LIGLST_'):
                ref = self.parser.tocleanstring(line.xpath('./td[2]')[0])
                tr = Transaction(ref)

                raw = self.parser.tocleanstring(line.xpath('./td[1]')[0])
                amount = self.parser.tocleanstring(line.xpath('./td')[-1])
                tr.parse(date=date, raw=raw)
                tr.set_amount(amount)
                yield tr
            elif line.find('td').attrib.get('class', '').startswith('PL_TOT'):
                m = re.search('(\d+/\d+/\d+)', line.xpath('./td')[0].text)
                if m:
                    date = m.group(1)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^(?:Vir(?:ement)?|VRT) (?P<text>.*)', re.I),
                 FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^CARTE(?: ETR.)? ' +
                            '(?P<dd>\d{2})/(?P<mm>\d{2})/(?P<yy>\d{4}) ' +
                            '(?P<text>.*)'),
                 FrenchTransaction.TYPE_CARD),
                (re.compile('^CHQ (?P<text>.*)$'),
                 FrenchTransaction.TYPE_CHECK),
                (re.compile('^RCH (?P<text>.*)'),
                 FrenchTransaction.TYPE_DEPOSIT)]

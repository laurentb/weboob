# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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

from weboob.tools.browser import BasePage
from weboob.capabilities.bank import Account
from weboob.capabilities import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


__all__ = ['AccountsListPage']


class AccountsListPage(BasePage):
    def get_list(self):
        for tr in self.document.getiterator('tr'):
            tds = tr.findall('td')
            if len(tds) != 3 or tds[0].find('a') is None or tds[0].find('a').attrib.get('class', '') != 'flecheM':
                continue

            account = Account()
            account.id = tds[1].text.strip()

            a = tds[0].findall('a')[-1]
            account.label = a.text.strip()
            account._link_id = a.attrib['href']

            m = re.search('(\w+)_IdPrestation', account._link_id)
            if not m or m.group(1) != 'CPT':
                account._link_id = None
                if m:
                    account.id += '.%s' % m.group(1)

            tag = tds[2].find('font')
            if tag is None:
                tag = tds[2]
            account.balance = Decimal(tag.text.replace('.','').replace(',','.').replace(' ', '').strip(u' \t\u20ac\xa0€\n\r'))
            account.coming = NotAvailable

            yield account

class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile('^VIR(EMENT)? (?P<text>.*)'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile('^PRLV (?P<text>.*)'),        FrenchTransaction.TYPE_ORDER),
                (re.compile('^CB (?P<text>.*)\s+(?P<dd>\d+)/(?P<mm>\d+)\s*(?P<loc>.*)'),
                                                          FrenchTransaction.TYPE_CARD),
                (re.compile('^DAB (?P<dd>\d{2})/(?P<mm>\d{2}) (?P<text>.*)'),
                                                          FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile('^CHEQUE$'),                  FrenchTransaction.TYPE_CHECK),
                (re.compile('^COTIS\.? (?P<text>.*)'),    FrenchTransaction.TYPE_BANK),
                (re.compile('^REMISE (?P<text>.*)'),      FrenchTransaction.TYPE_DEPOSIT),
               ]

class HistoryPage(BasePage):
    def get_operations(self):
        for script in self.document.getiterator('script'):
            if script.text is None or script.text.find('\nCL(0') < 0:
                continue

            for m in re.finditer(r"CL\((\d+),'(.+)','(.+)','(.+)','([\d -\.,]+)',('([\d -\.,]+)',)?'\d+','\d+','[\w\s]+'\);", script.text, flags=re.MULTILINE):
                op = Transaction(m.group(1))
                op.parse(date=m.group(3), raw=re.sub(u'[ ]+', u' ', m.group(4).replace(u'\n', u' ')))
                op.set_amount(m.group(5))
                op._coming = (re.match('\d+/\d+/\d+', m.group(2)) is None)
                yield op

# -*- coding: utf-8 -*-

# Copyright(C) 2014  Romain Bignon
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

import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from weboob.deprecated.browser import Page
from weboob.deprecated.browser.parsers.csvparser import CsvParser
from weboob.capabilities.bank import Account, AccountNotFound

from .accounthistory import Transaction, AccountHistory

class RedirectPage(Page):
    pass

class HistoryParser(CsvParser):
    FMTPARAMS = {'delimiter': ';'}


class ProAccountsList(Page):
    def get_accounts_list(self):
        for tr in self.document.xpath('//div[@class="comptestabl"]/table/tbody/tr'):
            cols = tr.findall('td')

            link = cols[0].find('a')
            if link is None:
                continue

            a = Account()
            a.id, a.label = map(unicode, link.attrib['title'].split(' ', 1))
            tmp_balance = self.parser.tocleanstring(cols[1])
            a.currency = a.get_currency(tmp_balance)
            a.balance = Decimal(Transaction.clean_amount(tmp_balance))
            a._card_links = []
            a._link_id = link.attrib['href']
            yield a

    def get_account(self, id):
        for account in self.get_accounts_list():
            if account.id == id:
                return account
        raise AccountNotFound('Unable to find account: %s' % id)

class ProAccountHistory(Page):
    def on_loaded(self):
        link = self.document.xpath('//a[contains(@href, "telechargercomptes.ea")]/@href')[0]
        self.browser.location(link)

class ProAccountHistoryDownload(Page):
    def on_loaded(self):
        self.browser.select_form(name='telechargement')
        self.browser['dateDebutPeriode'] = (datetime.date.today() - relativedelta(months=11)).strftime('%d/%m/%Y')
        self.browser.submit()

class ProAccountHistoryCSV(AccountHistory):
    def get_next_link(self):
        return False

    def get_history(self, deferred=False):
        for line in self.document.rows:
            if len(line) < 4 or line[0] == 'Date':
                continue
            t = Transaction()
            t.parse(raw=line[1], date=line[0])
            t.set_amount(line[2])
            t._coming = False
            yield t

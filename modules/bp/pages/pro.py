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

from weboob.browser.filters.standard import CleanText
from weboob.deprecated.browser import Page
from weboob.deprecated.browser.parsers.csvparser import CsvParser
from weboob.capabilities.bank import Account, AccountNotFound

from .accounthistory import Transaction, AccountHistory

class RedirectPage(Page):
    def check_for_perso(self):
        return self.document.xpath(u'//p[contains(text(), "L\'identifiant utilisé est celui d\'un compte de Particuliers")]')


class HistoryParser(CsvParser):
    FMTPARAMS = {'delimiter': ';'}


class ProAccountsList(Page):
    ACCOUNT_TYPES = {u'Comptes titres': Account.TYPE_MARKET,
                     u'Comptes Ã©pargne':    Account.TYPE_SAVINGS,
                     u'Comptes courants':    Account.TYPE_CHECKING,
                    }
    def get_accounts_list(self):
        for table in self.document.xpath('//div[@class="comptestabl"]/table'):
            try:
                account_type = self.ACCOUNT_TYPES[table.get('summary')]
                if not account_type:
                    account_type = self.ACCOUNT_TYPES[table.xpath('./caption/text()')[0].strip()]
            except (IndexError,KeyError):
                account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tbody/tr'):
                cols = tr.findall('td')

                link = cols[0].find('a')
                if link is None:
                    continue

                a = Account()
                a.type = account_type
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
        operations = []
        for line in self.document.rows:
            if len(line) < 4 or line[0] == 'Date':
                continue
            t = Transaction()
            t.parse(raw=line[1], date=line[0])
            t.set_amount(line[2])
            t._coming = False
            operations.append(t)
        operations = sorted(operations,
                      lambda a, b: cmp(a.date, b.date), reverse=True)
        for op in operations:
            yield op


class DownloadRib(Page):
    def get_rib_value(self, acc_id):
        opt = self.document.xpath('//div[@class="rechform"]//option')
        for o in opt:
            if acc_id in o.text:
                return o.xpath('./@value')[0]
        return None

class RibPage(Page):
    def get_iban(self):
        if self.document.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]'):
            return CleanText()\
                .filter(self.document.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]')[0])\
                .replace(' ', '').strip()
        return None

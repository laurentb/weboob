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

import re
import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from urlparse import urljoin

from weboob.browser.filters.standard import CleanText
from weboob.browser.pages import LoggedPage, CsvPage
from weboob.capabilities.bank import Account

from .accounthistory import Transaction
from .base import MyHTMLPage


class RedirectPage(LoggedPage, MyHTMLPage):
    def check_for_perso(self):
        return self.doc.xpath(u'//p[contains(text(), "L\'identifiant utilisé est celui d\'un compte de Particuliers")]')


class ProAccountsList(LoggedPage, MyHTMLPage):
    ACCOUNT_TYPES = {u'comptes titres': Account.TYPE_MARKET,
                     u'comptes Ã©pargne':    Account.TYPE_SAVINGS,
                     # wtf? ^
                     u'comptes épargne':     Account.TYPE_SAVINGS,
                     u'comptes courants':    Account.TYPE_CHECKING,
                    }
    def get_accounts_list(self):
        for table in self.doc.xpath('//div[@class="comptestabl"]/table'):
            try:
                account_type = self.ACCOUNT_TYPES[table.get('summary').lower()]
                if not account_type:
                    account_type = self.ACCOUNT_TYPES[table.xpath('./caption/text()')[0].strip().lower()]
            except (IndexError,KeyError):
                account_type = Account.TYPE_UNKNOWN
            for tr in table.xpath('./tbody/tr'):
                cols = tr.findall('td')

                link = cols[0].find('a')
                if link is None:
                    continue

                a = Account()
                a.type = account_type
                a.id = unicode(re.search('([A-Z\d]{4}[A-Z\d\*]{3}[A-Z\d]{4})', link.attrib['title']).group(1))
                a.label = unicode(link.attrib['title'].replace('%s ' % a.id, ''))
                tmp_balance = CleanText(None).filter(cols[1])
                a.currency = a.get_currency(tmp_balance)
                if not a.currency:
                    a.currency = u'EUR'
                a.balance = Decimal(Transaction.clean_amount(tmp_balance))
                a._has_cards = False
                a._link_id = urljoin(self.url, link.attrib['href'])
                yield a


class ProAccountHistory(LoggedPage, MyHTMLPage):
    def on_load(self):
        MyHTMLPage.on_load(self)
        link = self.doc.xpath('//a[contains(@href, "telechargercomptes.ea")]/@href')[0]
        self.browser.location(link)


class ProAccountHistoryDownload(LoggedPage, MyHTMLPage):
    def on_load(self):
        MyHTMLPage.on_load(self)
        form = self.get_form(name='telechargement')
        form['dateDebutPeriode'] = (datetime.date.today() - relativedelta(months=11)).strftime('%d/%m/%Y')
        form.submit()


class ProAccountHistoryCSV(LoggedPage, CsvPage):
    def decode_row(self, row, encoding):
        try:
            return [unicode(cell, encoding) for cell in row]
        except UnicodeDecodeError:
            return ''

    FMTPARAMS = {'delimiter': ';'}

    def get_next_link(self):
        return False

    def get_history(self, deferred=False):
        operations = []
        for line in self.doc:
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


class DownloadRib(LoggedPage, MyHTMLPage):
    def get_rib_value(self, acc_id):
        opt = self.doc.xpath('//div[@class="rechform"]//option')
        for o in opt:
            if acc_id in o.text:
                return o.xpath('./@value')[0]
        return None


class RibPage(LoggedPage, MyHTMLPage):
    def get_iban(self):
        if self.doc.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]'):
            return CleanText()\
                .filter(self.doc.xpath('//div[@class="blocbleu"][2]//table[@class="datalist"]')[0])\
                .replace(' ', '').strip()
        return None

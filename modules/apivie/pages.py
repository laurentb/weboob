# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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

from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.browser.pages import LoggedPage, HTMLPage
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.browser.filters.standard import Date, CleanText
from weboob.browser.filters.html import Attr


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(nr=0)
        form['_58_login'] = username.encode('utf-8')
        form['_58_password'] = password.encode('utf-8')
        return form.submit()


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {u'APIVIE': Account.TYPE_LIFE_INSURANCE,
             u'LINXEA ZEN CLIENT': Account.TYPE_LIFE_INSURANCE,
             u'PERP': Account.TYPE_PERP
            }

    COL_LABEL = 0
    COL_OWNER = 1
    COL_ID = 2
    COL_AMOUNT = 3

    def iter_accounts(self):
        for line in self.doc.xpath('//table[@summary="informations contrat"]/tbody/tr'):
            yield self._get_account(line)

    def _get_account(self, line):
        cleaner = CleanText().filter

        tds = line.findall('td')
        account = Account()
        account.id = cleaner(tds[self.COL_ID])
        account.label = cleaner(tds[self.COL_LABEL])
        tlabel = Attr('//a[contains(@class, "logo")]/img', 'alt')(self.doc).upper()
        account.type = self.TYPES.get(tlabel, Account.TYPE_UNKNOWN)
        balance_str = cleaner(tds[self.COL_AMOUNT])
        account.balance = Decimal(FrenchTransaction.clean_amount(balance_str))
        account.currency = account.get_currency(balance_str)
        return account


class InvestmentsPage(LoggedPage, HTMLPage):
    COL_LABEL = 0
    COL_CODE = 1
    COL_VALUATION = 2
    COL_PORTFOLIO_SHARE = 3

    def iter_investment(self):
        cleaner = CleanText().filter

        for line in self.doc.xpath('//div[@class="supportTable"]//table/tbody/tr'):
            tds = line.findall('td')
            if len(tds) < 4:
                continue
            inv = Investment()

            if self.doc.xpath('//div[@id="table-evolution-contrat"]//table/tbody/tr[1]/td[1]'):
                inv.vdate = Date(dayfirst=True).filter(CleanText().filter(
                        self.doc.xpath('//div[@id="table-evolution-contrat"]//table/tbody/tr[1]/td[1]')))
            else:
                inv.vdate = NotAvailable
            inv.label = cleaner(tds[self.COL_LABEL])
            inv.code = cleaner(tds[self.COL_CODE])
            inv.valuation = Decimal(FrenchTransaction.clean_amount(
                            cleaner(tds[self.COL_VALUATION])))
            inv.portfolio_share = Decimal(FrenchTransaction.clean_amount(
                                  cleaner(tds[self.COL_PORTFOLIO_SHARE]))) / 100
            yield inv


class Transaction(FrenchTransaction):
    pass


class OperationsPage(LoggedPage, HTMLPage):
    COL_DATE = 0
    COL_LABEL = 1
    COL_AMOUNT = 2

    def iter_history(self):
        cleaner = CleanText().filter

        for line in self.doc.xpath('//table[@role="treegrid"]/tbody/tr'):
            tds = line.findall('td')

            operation = Transaction()

            date = cleaner(tds[self.COL_DATE])
            label = cleaner(tds[self.COL_LABEL])
            amount = cleaner(tds[self.COL_AMOUNT])

            if len(amount) == 0:
                continue

            color = tds[self.COL_AMOUNT].find('span').attrib['class']
            if color == 'black':
                continue

            operation.parse(date, label)
            operation.set_amount(amount)

            if color == 'red' and operation.amount > 0:
                operation.amount = - operation.amount

            yield operation

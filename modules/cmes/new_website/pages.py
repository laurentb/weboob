# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, ItemElement, method
from weboob.browser.filters.standard import (
    CleanText, Date, Regexp, Field, Currency, Upper, MapIn, Eval
)
from weboob.capabilities.bank import Account, Investment, Pocket

from ..pages import MyDecimal, Transaction


ACCOUNTS_TYPES = {
    "pargne entreprise": Account.TYPE_PEE,
    "pargne retraite": Account.TYPE_PERCO
}


class NewAccountsPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//th[text()= "Nom du support" or text()="Nom du profil"]/ancestor::table/ancestor::table'

        class item(ItemElement):
            klass = Account
            balance_xpath = './/span[contains(text(), "Montant total")]/following-sibling::span'

            obj_label = CleanText('./tbody/tr/th//div')
            obj_balance = MyDecimal(balance_xpath)
            obj_currency = Currency(balance_xpath)
            obj_type = MapIn(Field('label'), ACCOUNTS_TYPES, Account.TYPE_UNKNOWN)

            def obj_id(self):
                # Use customer number + label to build account id
                number = Regexp(CleanText('//div[@id="ei_tpl_fullSite"]//div[contains(@class, "ei_tpl_profil_content")]/p'),
                                r'(\d+)$', '\\1')(self)
                return Field('label')(self) + number

    def iter_invest_rows(self, account):
        for row in self.doc.xpath('//th/div[contains(., "%s")]/ancestor::table//table/tbody/tr' % account.label):
            idx = re.search(r'_(\d+)\.', row.xpath('.//a[contains(@href, "GoFund")]/@id')[0]).group(1)
            yield idx, row

    def iter_investment(self, account):
        for idx, row in self.iter_invest_rows(account=account):
            inv = Investment()
            inv._account = account
            inv._idx = idx
            inv.label = CleanText('.//a[contains(@href, "GoFund")]/text()')(row)
            inv.valuation = MyDecimal('.//td[2]')(row)
            inv.diff_ratio = Eval(lambda x: x / 100, MyDecimal('.//td[3]'))(row)

            # Get data from a popup not reachable from the current row
            inv.diff = MyDecimal('//div[@id="I0:F1_%s.R20:D"]//span' % idx)(self.doc)

            if account.balance != 0:
                inv.portfolio_share = inv.valuation / account.balance
            yield inv

    def iter_pocket(self, inv):
        for idx, _ in self.iter_invest_rows(account=inv._account):
            if idx != inv._idx:
                continue

            for row in self.doc.xpath('//div[@id="I0:F1_%s.R16:D"]//tr[position()>1]' % idx):
                pocket = Pocket()
                pocket.label = inv.label
                pocket.investment = inv
                pocket.amount = MyDecimal('./td[2]')(row)

                if 'DISPONIBLE' in Upper(CleanText('./td[1]'))(row):
                    pocket.condition = Pocket.CONDITION_AVAILABLE
                else:
                    pocket.condition = Pocket.CONDITION_DATE
                    pocket.availability_date = Date(Regexp(Upper(CleanText('./td[1]')), 'AU[\s]+(.*)'), dayfirst=True)(row)

                yield pocket


class OperationPage(LoggedPage, HTMLPage):
    @method
    class get_transaction(ItemElement):
        klass = Transaction

        obj_amount = MyDecimal('//td[contains(text(), "Montant total")]/following-sibling::td')
        obj_label = CleanText('(//p[contains(@id, "smltitle")])[2]')
        obj_raw = Transaction.Raw(Field('label'))
        obj_date = Date(Regexp(CleanText('(//p[contains(@id, "smltitle")])[1]'), r'(\d{1,2}/\d{1,2}/\d+)'), dayfirst=True)
        obj__account_label = CleanText('//td[contains(text(), "Montant total")]/../following-sibling::tr/th[1]')


class OperationsListPage(LoggedPage, HTMLPage):
    def __init__(self, *a, **kw):
        self._cache = []
        super(OperationsListPage, self).__init__(*a, **kw)

    def get_operations_idx(self):
        return [i.split(':')[-1] for i in self.doc.xpath('.//input[contains(@name, "_FID_GoOperationDetails")]/@name')]

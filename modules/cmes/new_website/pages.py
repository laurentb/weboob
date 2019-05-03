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
    CleanText, CleanDecimal, Date, Regexp, Field, Currency, Upper, MapIn, Eval
)
from weboob.capabilities.bank import Account, Investment, Pocket, NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>.*[Vv]ersement.*)'),  FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>([Aa]rbitrage|[Pp]rélèvements.*))'), FrenchTransaction.TYPE_ORDER),
                (re.compile(u'^(?P<text>([Rr]etrait|[Pp]aiement.*))'), FrenchTransaction.TYPE_WITHDRAWAL),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form(name="bloc_ident")
        form['_cm_user'] = login
        form['_cm_pwd'] = password
        form.submit()


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
        """
        Process each invest row, extract elements needed to get
        pocket and valuation diff information.
        There are even PERCO rows where invests are located into a 'repartition' element.
        Returns (row, el_repartition, el_pocket, el_diff)
        """
        for row in self.doc.xpath('//th/div[contains(., "%s")]/ancestor::table//table/tbody/tr' % account.label):
            id_repartition = row.xpath('.//td[1]//span[contains(@id, "rootSpan")]/@id')
            id_pocket = row.xpath('.//td[2]//span[contains(@id, "rootSpan")]/@id')
            id_diff = row.xpath('.//td[3]//span[contains(@id, "rootSpan")]/@id')

            yield (
                row,
                row.xpath('//div[contains(@id, "dv::s::%s")]' % id_repartition[0].rsplit(':', 1)[0])[0] if id_repartition else None,
                row.xpath('//div[contains(@id, "dv::s::%s")]' % id_pocket[0].rsplit(':', 1)[0])[0] if id_pocket else None,
                row.xpath('//div[contains(@id, "dv::s::%s")]' % id_diff[0].rsplit(':', 1)[0])[0] if id_diff else None,
            )

    def iter_investment(self, account):
        for row, elem_repartition, elem_pocket, elem_diff in self.iter_invest_rows(account=account):
            inv = Investment()
            inv._account = account
            inv._el_pocket = elem_pocket
            inv.label = CleanText('.//td[1]')(row)
            inv.valuation = MyDecimal('.//td[2]')(row)

            # On all Cmes children the row shows percentages and the popup shows absolute values in currency.
            # On Cmes it is mirrored, the popup contains the percentage.
            is_mirrored = '%' in row.text_content()

            if not is_mirrored:
                inv.diff = MyDecimal('.//td[3]')(row)
                if elem_diff is not None:
                    inv.diff_ratio = Eval(lambda x: x / 100,
                                          MyDecimal(Regexp(CleanText('.'), r'([+-]?[\d\s]+[\d,]+)\s*%')))(elem_diff)
            else:
                inv.diff = MyDecimal('.')(elem_diff)
                if elem_diff is not None:
                    inv.diff_ratio = Eval(lambda x: x / 100,
                                          MyDecimal(Regexp(CleanText('.//td[3]'), r'([+-]?[\d\s]+[\d,]+)\s*%')))(row)

            if account.balance != 0:
                inv.portfolio_share = inv.valuation / account.balance
            yield inv

    def iter_pocket(self, inv):
        if inv._el_pocket:
            for i, row in enumerate(inv._el_pocket.xpath('.//tr[position()>1]')):
                pocket = Pocket()
                pocket.id = "%s%s%s" % (inv._account.label, inv.label, i)
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

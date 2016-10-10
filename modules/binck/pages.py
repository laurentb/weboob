# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, TableElement, DictElement, method
from weboob.browser.filters.standard import CleanText, Date, Format, CleanDecimal, Eval, Env, TableCell
from weboob.browser.filters.html import Attr
from weboob.browser.filters.json import Dict
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@class="logon-form"]')
        form['UserName'] = login
        form['Password'] = password
        form.submit()

    def get_error(self):
        return CleanText('//div[contains(@class, "errors")]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {u'LIVRET':         Account.TYPE_SAVINGS,
             u'COMPTE-TITRES':  Account.TYPE_MARKET,
             u'PEA-PME':        Account.TYPE_PEA,
             u'PEA':            Account.TYPE_PEA
            }

    def go_toaccount(self, number):
        form = self.get_form('//form[contains(@action, "Switch")]')
        form['accountNumber'] = number
        form.submit()

    def get_iban(self):
        return CleanText('//div[@class="iban"]/text()', replace=[(' ', '')], default=NotAvailable)(self.doc)

    def get_token(self):
        return [{Attr('.', 'name')(input): Attr('.', 'value')(input)} \
            for input in self.doc.xpath('//input[contains(@name, "Token")]')][0]

    def is_investment(self):
        return CleanText('//header/a[contains(@href, "Portfolio")]', default=False)(self.doc)

    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[contains(@class, "accountsTable")]/tbody/tr'
        head_xpath = '//table[contains(@class, "accountsTable")]/thead/tr/th'

        col_label = u'Intitulé du compte'
        col_balance = u'Total Portefeuille'

        class item(ItemElement):
            klass = Account

            obj_id = Attr('.', 'data-accountnumber')
            obj_label = CleanText(TableCell('label'))
            obj_balance = MyDecimal(TableCell('balance'))

            def obj_type(self):
                return self.page.TYPES.get(CleanText('./ancestor::section[h1]/h1')(self).upper(), Account.TYPE_UNKNOWN)

            def obj_currency(self):
                return Account.get_currency(CleanText(TableCell('balance'))(self))


class InvestmentPage(LoggedPage, JsonPage):
    def get_valuation_diff(self):
        return CleanDecimal().filter(Dict('PortfolioSummary/UnrealizedResultValue')(self.doc))

    @method
    class iter_investment(DictElement):
        item_xpath = 'PortfolioOverviewGroups/*/Items'

        def parse(self, el):
            self.env['vdate'] = Date(dayfirst=True).filter(Dict('PortfolioSummary/UpdatedAt')(self.page.doc))

        class item(ItemElement):
            klass = Investment

            obj_label = Dict('SecurityName')
            obj_code = Dict('IsinCode')
            obj_quantity = MyDecimal(Dict('Quantity'))
            obj_vdate = Env('vdate')

            obj_valuation = MyDecimal(Dict('ValueInEuro'))
            obj_unitvalue = MyDecimal(Dict('Quote'))
            obj_unitprice = MyDecimal(Dict('HistoricQuote'))
            obj_diff = MyDecimal(Dict('ResultValueInEuro'))
            obj_diff_percent = Eval(lambda x: x / 100, MyDecimal(Dict('ResultPercentageInEuro')))

            obj_original_currency = Dict('CurrencyCode')
            obj_original_valuation = MyDecimal(Dict('ValueInSecurityCurrency'))
            obj_original_diff = MyDecimal(Dict('ResultValueInSecurityCurrency'))


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(u'^(?P<text>(Virement.*|Transfert.*))'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(u'^(?P<text>Dépôt.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(u'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
               ]


class HistoryPage(LoggedPage, JsonPage):
    def get_nextpage_data(self, data):
        data.append(('direction', "0"))
        data.append(('lastSequenceNumber', Dict('LastSequenceNumber')(self.doc)))
        data.append(('currentPage', Dict('CurrentPage')(self.doc)))
        data.extend([('pages', x) for x in self.doc['Pages']])
        return data

    @method
    class iter_history(DictElement):
        item_xpath = 'Transactions'

        class item(ItemElement):
            klass = Transaction

            condition = lambda self: MyDecimal(Dict('Mutation'))(self.el)

            obj_raw = Transaction.Raw(Format('%s %s', Dict('Type'), Dict('Description')))
            obj_date = Date(Dict('Date'), dayfirst=True)
            obj_amount = MyDecimal(Dict('Mutation'))

            def obj_id(self):
                return str(Dict('TransactionId')(self))

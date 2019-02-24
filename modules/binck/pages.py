# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import re

from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Date, Format, CleanDecimal, Eval, Env, Field
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.browser.filters.json import Dict
from weboob.exceptions import BrowserPasswordExpired, ActionNeeded
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class QuestionPage(HTMLPage):
    def on_load(self):
        form = self.get_form('//form[@action="/FDL_Complex_FR_Compte/Introduction/SkipQuestionnaire"]')
        form.submit()


class ViewPage(LoggedPage, HTMLPage):
    # We automatically skip the new website tutorial
    def on_load(self):
        link = Link('//a[contains(@href, "Skip") and contains(text(), "Suivant")]')(self.doc)
        assert link, 'ViewPage skipping link was not found'
        self.browser.location(link)


class HomePage(LoggedPage, HTMLPage):
    # We directly go from the home page to the accounts page
    def on_load(self):
        ''' Remove the old_website_connection part when old website is obsolete '''
        if self.browser.old_website_connection:
            self.browser.location('https://web.binck.fr/AccountsOverview/Index')
        else:
            self.browser.location('https://web.binck.fr/PersonAccountOverview/Index')


class ChangePassPage(LoggedPage, HTMLPage):
    def on_load(self):
        message = CleanText('//h3')(self.doc)
        raise BrowserPasswordExpired(message)


class LogonFlowPage(HTMLPage):
    def on_load(self):
        raise ActionNeeded(CleanText('//article//h1 | //article//h3')(self.doc))


class LoginPage(HTMLPage):
    def login(self, login, password):
        form = self.get_form('//form[@class="logon-form"]')
        form['UserName'] = login
        form['Password'] = password
        form.submit()

    def get_error(self):
        return CleanText('//div[contains(@class, "errors")]')(self.doc)


class AccountsPage(LoggedPage, HTMLPage):
    TYPES = {'L': Account.TYPE_SAVINGS,
             'CT': Account.TYPE_MARKET,
             'PEA': Account.TYPE_PEA,
             'PEA-PME': Account.TYPE_PEA,
             'AV': Account.TYPE_LIFE_INSURANCE,
            }

    ''' Delete this method when the old website is obsolete '''
    def has_accounts_table(self):
        return self.doc.xpath('//table[contains(@class, "accountoverview-table")]')

    def get_token(self):
        return [{Attr('.', 'name')(input): Attr('.', 'value')(input)} \
            for input in self.doc.xpath('//input[contains(@name, "Token")]')][0]

    @method
    class iter_accounts(ListElement):
        # Tables have no headers so we must use ListElement.
        # We use the 'has-class("")' to skip Life Insurance ads
        item_xpath = '//table[contains(@class, "accountoverview-table")]/tbody/tr[has-class("")]'

        class item(ItemElement):
            klass = Account

            obj_id = Attr('.', 'data-account-number')
            obj_balance = MyDecimal('.//div[contains(text(), "Total des avoirs")]/following::strong[1]')
            obj__liquidity = MyDecimal('.//div[contains(text(), "Espèces")]/following::strong[1]')

            def obj_label(self):
                raw_label = ' '.join(CleanText('./td[1]')(self).split()[1:])
                # Remove IBAN from label:
                return re.sub(' [A-Z\d]{16,}', '', raw_label)

            def obj_iban(self):
                return CleanText('.//h6')(self) or NotAvailable

            def obj_type(self):
                return self.page.TYPES.get(CleanText('.//div[contains(@class, "circle-background")]/span')(self), Account.TYPE_UNKNOWN)

            def obj_currency(self):
                return Account.get_currency(CleanText('.//div[contains(text(), "Total des avoirs")]/following::strong[1]')(self))


class OldAccountsPage(LoggedPage, HTMLPage):
    '''
    Old website accounts page. We can get rid of this
    class when all users have access to the new website.
    '''
    TYPES = {'LIVRET':         Account.TYPE_SAVINGS,
             'COMPTE-TITRES':  Account.TYPE_MARKET,
             'PEA-PME':        Account.TYPE_PEA,
             'PEA':            Account.TYPE_PEA
            }

    def go_to_account(self, number):
        form = self.get_form('//form[contains(@action, "Switch")]')
        form['accountNumber'] = number
        form.submit()

    def get_iban(self):
        return CleanText('//div[@class="iban"]/text()', replace=[(' ', '')], default=NotAvailable)(self.doc)

    def get_token(self):
        return [{Attr('.', 'name')(input): Attr('.', 'value')(input)} \
            for input in self.doc.xpath('//input[contains(@name, "Token")]')][0]

    def is_investment(self):
        # warning: the link can be present even in case of non-investement account
        return CleanText('//a[contains(@href, "Portfolio")]', default=False)(self.doc)

    @method
    class iter_accounts(TableElement):
        item_xpath = '//table[contains(@class, "accountsTable")]/tbody/tr'
        head_xpath = '//table[contains(@class, "accountsTable")]/thead/tr/th'

        col_label = 'Intitulé du compte'
        col_balance = 'Total Portefeuille'
        col_liquidity = 'Espèces'

        class item(ItemElement):
            klass = Account

            obj_id = Attr('.', 'data-accountnumber')
            obj_label = CleanText(TableCell('label'))
            obj_balance = MyDecimal(TableCell('balance'))
            obj__liquidity = MyDecimal(TableCell('liquidity'))

            def obj_type(self):
                return self.page.TYPES.get(CleanText('./ancestor::section[h1]/h1')(self).upper(), Account.TYPE_UNKNOWN)

            def obj_currency(self):
                return Account.get_currency(CleanText(TableCell('balance'))(self))


class SwitchPage(LoggedPage, HTMLPage):
    pass


class InvestmentPage(LoggedPage, JsonPage):
    def get_valuation_diff(self):
        return CleanDecimal().filter(Dict('PortfolioSummary/UnrealizedResultValue')(self.doc))

    @method
    class iter_investment(DictElement):
        item_xpath = 'PortfolioOverviewGroups/*/Items'

        class item(ItemElement):
            klass = Investment

            obj_label = Dict('SecurityName')
            obj_quantity = MyDecimal(Dict('Quantity'))
            obj_vdate = Env('vdate')
            obj_unitvalue = Env('unitvalue', default=NotAvailable)
            obj_unitprice = Env('unitprice', default=NotAvailable)
            obj_valuation = MyDecimal(Dict('ValueInEuro'))
            obj_diff = MyDecimal(Dict('ResultValueInEuro'))
            obj_diff_percent = Eval(lambda x: x / 100, MyDecimal(Dict('ResultPercentageInEuro')))
            obj_original_currency = Env('o_currency', default=NotAvailable)
            obj_original_unitvalue = Env('o_unitvalue', default=NotAvailable)
            obj_original_unitprice = Env('o_unitprice', default=NotAvailable)
            obj_original_valuation = Env('o_valuation', default=NotAvailable)
            obj_original_diff = Env('o_diff', default=NotAvailable)
            obj__security_id = Dict('SecurityId')

            def obj_code(self):
                if is_isin_valid(Dict('IsinCode')(self)):
                    return Dict('IsinCode')(self)
                elif "espèces" in Field('label')(self).lower():
                    return "XX-liquidity"
                return NotAvailable

            def obj_code_type(self):
                if is_isin_valid(Field('code')(self)):
                    return Investment.CODE_TYPE_ISIN
                return NotAvailable

            def parse(self, el):
                if self.env['currency'] != CleanText(Dict('CurrencyCode'))(self):
                    self.env['o_currency'] = CleanText(Dict('CurrencyCode'))(self)
                    self.env['o_unitvalue'] = MyDecimal(Dict('Quote'))(self)
                    self.env['o_unitprice'] = MyDecimal(Dict('HistoricQuote'))(self)
                    self.env['o_valuation'] = MyDecimal(Dict('ValueInSecurityCurrency'))(self)
                    self.env['o_diff'] = MyDecimal(Dict('ResultValueInSecurityCurrency'))(self)
                else:
                    self.env['unitvalue'] = MyDecimal(Dict('Quote'))(self)
                    self.env['unitprice'] = MyDecimal(Dict('HistoricQuote'))(self)
                self.env['vdate'] = Date(dayfirst=True).filter(Dict('PortfolioSummary/UpdatedAt')(self.page.doc))


class InvestmentListPage(LoggedPage, HTMLPage):
    pass


class InvestDetailPage(LoggedPage, HTMLPage):
    def get_isin_code_and_type(self):
        code = CleanText('//td[strong[text()="ISIN"]]/following-sibling::td[1]', default=NotAvailable)(self.doc)
        if is_isin_valid(code):
            return code, Investment.CODE_TYPE_ISIN
        return NotAvailable, NotAvailable


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>(Virement.*|Transfert.*))'), FrenchTransaction.TYPE_TRANSFER),
                (re.compile(r'^(?P<text>Dépôt.*)'), FrenchTransaction.TYPE_DEPOSIT),
                (re.compile(r'^(?P<text>.*)'), FrenchTransaction.TYPE_BANK),
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

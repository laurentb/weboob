# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser.pages import HTMLPage, JsonPage, LoggedPage
from weboob.browser.elements import ItemElement, ListElement, DictElement, TableElement, method
from weboob.browser.filters.standard import CleanText, Date, DateTime, Format, CleanDecimal, Eval, Env, Field
from weboob.browser.filters.html import Attr, Link, TableCell
from weboob.browser.filters.json import Dict
from weboob.exceptions import BrowserPasswordExpired, ActionNeeded
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable, empty
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.capabilities.bank.investments import is_isin_valid
from weboob.browser.filters.standard import FilterError


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class QuestionPage(HTMLPage):
    def on_load(self):
        if self.doc.xpath(u'//h1[contains(text(), "Questionnaires connaissance et expérience")]'):
            form = self.get_form('//form[@action="/FsmaMandatoryQuestionnairesOverview/PostponeQuestionnaires"]')
        else:
            form = self.get_form('//form[contains(@action, "Complex_FR_Compte/Introduction/SkipQuestionnaire")]')
        form.submit()


class BinckPage(LoggedPage, HTMLPage):
    # Used to factorize the get_token() method
    def get_token(self):
        return [{Attr('.', 'name')(input): Attr('.', 'value')(input)}
            for input in self.doc.xpath('//input[contains(@name, "Token")]')][0]


class ViewPage(LoggedPage, HTMLPage):
    # We automatically skip the new website tutorial
    def on_load(self):
        link = Link('//a[contains(@href, "Skip") and contains(text(), "Suivant")]')(self.doc)
        assert link, 'ViewPage skipping link was not found'
        self.browser.location(link)


class HomePage(LoggedPage, HTMLPage):
    # We directly go from the home page to the accounts page
    def on_load(self):
        if self.browser.old_website_connection:
            accounts_url = 'https://web.binck.fr/AccountsOverview/Index'
        elif self.doc.xpath('//a[text()="Mes comptes Binck"]'):
            accounts_url = 'https://web.binck.fr/PersonAccountOverview/Index'
        elif self.doc.xpath('//a[span[text()="Portefeuille"]][@role="button"]'):
            self.browser.unique_account = True
            accounts_url = 'https://web.binck.fr/PortfolioOverview/Index'
        assert accounts_url, 'The accounts URL of this connection is not handled yet!'
        self.browser.location(accounts_url)


class ChangePassPage(LoggedPage, HTMLPage):
    def on_load(self):
        message = CleanText('//h3')(self.doc) or CleanText('//h1')(self.doc)
        raise BrowserPasswordExpired(message)


class HandlePasswordsPage(BinckPage):
    def on_load(self):
        token = self.get_token()
        self.browser.postpone_passwords.go(headers=token, method='POST')
        self.browser.home_page.go()


class PostponePasswords(LoggedPage, HTMLPage):
    pass

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


class AccountsPage(BinckPage):
    TYPES = {'L': Account.TYPE_SAVINGS,
             'CT': Account.TYPE_MARKET,
             'PEA': Account.TYPE_PEA,
             'PEA-PME': Account.TYPE_PEA,
             'AV': Account.TYPE_LIFE_INSURANCE,
            }

    ''' Delete this method when the old website is obsolete '''
    def has_accounts_table(self):
        return self.doc.xpath('//table[contains(@class, "accountoverview-table")]')

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


class OldAccountsPage(BinckPage):
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
            obj_vdate = DateTime(CleanText(Dict('Time')), dayfirst=True, strict=False)
            obj_unitvalue = Env('unitvalue', default=NotAvailable)
            obj_unitprice = Env('unitprice', default=NotAvailable)
            obj_valuation = MyDecimal(Dict('ValueInEuro'))
            obj_diff = MyDecimal(Dict('ResultValueInEuro'))
            obj_diff_ratio = Eval(lambda x: x / 100, MyDecimal(Dict('ResultPercentageInEuro')))
            obj_original_currency = Env('o_currency', default=NotAvailable)
            obj_original_unitvalue = Env('o_unitvalue', default=NotAvailable)
            obj_original_unitprice = Env('o_unitprice', default=NotAvailable)
            obj_original_valuation = Env('o_valuation', default=NotAvailable)
            obj_original_diff = Env('o_diff', default=NotAvailable)
            obj__security_id = Dict('SecurityId')

            def obj_vdate(self):
                try:
                    # during stocks closing hours only date (d/m/y) is given
                    return Date(CleanText(Dict('Time')), dayfirst=True)(self)
                except FilterError:
                    # during stocks opening hours only time (h:m:s) is given,
                    # can even be realtime, depending on user settings,
                    # can be given in foreign markets time,
                    # e.g. 10:00 is displayed at 9:00 for an action in NASADQ Helsinki market
                    return DateTime(CleanText(Dict('Time')), dayfirst=True, strict=False)(self)

            def obj_code(self):
                if is_isin_valid(Dict('IsinCode')(self)):
                    return Dict('IsinCode')(self)
                elif "espèces" in Field('label')(self).lower():
                    return "XX-liquidity"
                return NotAvailable

            def obj_code_type(self):
                if empty(Field('code')(self)):
                    return NotAvailable
                return Investment.CODE_TYPE_ISIN

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

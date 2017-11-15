# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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

from __future__ import unicode_literals

import re

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.standard import (
    Regexp, Field, CleanText, CleanDecimal, Eval, Currency
)
from weboob.browser.filters.html import Link, TableCell
from weboob.capabilities.bank import Account, Investment
from weboob.capabilities.base import NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction


def MyDecimal(*args, **kwargs):
    kwargs.update(replace_dots=True, default=NotAvailable)
    return CleanDecimal(*args, **kwargs)


class LoginPage(HTMLPage):
    def enter_login(self, username):
        form = self.get_form(nr=1)
        form['name'] = username
        form.submit()

    def enter_password(self, password):
        form = self.get_form(nr=1)
        form['pass'] = password
        form.submit()


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>.*?) (?P<dd>\d{2})/(?P<mm>\d{2})$'), FrenchTransaction.TYPE_CARD)]


class item_account_generic(ItemElement):
    """Generic accounts properties for Carrefour homepage"""
    klass = Account

    def obj_balance(self):
        balance = CleanDecimal('.//div[contains(@class, "right_col")]//h2[1]', replace_dots=True)(self)
        return (-balance if Field('type')(self) in (Account.TYPE_LOAN,) else balance)

    obj_currency = Currency('.//div[contains(@class, "right_col")]//h2[1]')
    obj_label = CleanText('.//div[contains(@class, "leftcol")]//h2[1]')
    obj_id = Regexp(CleanText('.//div[contains(@class, "leftcol")]//p'), ":\s+([\d]+)")
    obj_number = Field('id')

    def obj_url(self):
        acc_number = Field('id')(self)
        xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a'.format(acc_number=acc_number)
        return Link(xpath_link)(self)


class iter_history_generic(Transaction.TransactionsElement):
    head_xpath = u'//div[*[contains(text(), "opérations")]]/table//thead/tr/th'
    item_xpath = u'//div[*[contains(text(), "opérations")]]/table/tbody/tr'

    def next_page(self):
        next_page = Link(u'//a[contains(text(), "précédentes")]', default=None)(self)
        if next_page:
            return "/%s" % next_page

    class item(Transaction.TransactionElement):
        def obj_type(self):
            return Transaction.TYPE_CARD if len(self.el.xpath('./td')) > 3 else Transaction.TYPE_BANK

        def condition(self):
            return TableCell('raw')(self)


class HomePage(LoggedPage, HTMLPage):

    @method
    class iter_loan_accounts(ListElement):  # Prêts
        item_xpath = '//div[@class="pp_espace_client"]'

        class item(item_account_generic):
            obj_type = Account.TYPE_LOAN

    @method
    class iter_card_accounts(ListElement):  # PASS cards
        item_xpath = '//div/div[contains(./h2, "Carte et Crédit") and contains(./p, "Numéro de compte")]/..'

        class item(item_account_generic):
            obj_type = Account.TYPE_CARD

            def obj_balance(self):
                available = CleanDecimal('.//p[contains(., "encours depuis le")]//preceding-sibling::h2', default=None, replace_dots=True)(self)
                return NotAvailable if not available else -available

    @method
    class iter_saving_accounts(ListElement):  # livrets
        item_xpath = (
            '//div[div[(contains(./h2, "Livret Carrefour") or contains(./h2, "Epargne PASS")) and contains(./p, "Numéro de compte")]]'
        )

        class item(item_account_generic):
            obj_type = Account.TYPE_SAVINGS
            obj_url = Link('.//a[contains(., "Historique des opérations")]')

            def obj_balance(self):
                val = CleanDecimal('.//a[contains(text(), "versement")]//preceding-sibling::h2', replace_dots=True, default=NotAvailable)(self)
                if val is not NotAvailable:
                    return val
                val = CleanDecimal(Regexp(CleanText('./div[@class="right_col_wrapper"]//h2'), r'([\d ,]+€)'), replace_dots=True)(self)
                return val

    @method
    class iter_life_accounts(ListElement):  # Assurances vie
        item_xpath = '//div/div[contains(./h2, "Carrefour Horizons") and contains(./p, "Numéro de compte")]/..'

        class item(item_account_generic):
            obj_type = Account.TYPE_LIFE_INSURANCE

            def obj_url(self):
                acc_number = Field('id')(self)
                xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a[contains(text(), "Dernieres opérations")]'.format(acc_number=acc_number)
                return Link(xpath_link)(self)

            def obj__life_investments(self):
                xpath_link = '//li[contains(., "{acc_number}")]/ul/li/a[contains(text(), "Solde")]'.format(acc_number=Field('id')(self))
                return Link(xpath_link)(self)


class TransactionsPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(iter_history_generic):
        pass


class SavingHistoryPage(LoggedPage, HTMLPage):
    @pagination
    @method
    class iter_history(iter_history_generic):
        head_xpath = '//table[@id="creditHistory" or @id="TransactionHistory"]/thead/tr/th'
        item_xpath = '//table[@id="creditHistory" or @id="TransactionHistory"]/tbody/tr'


class LifeInvestmentsPage(LoggedPage, HTMLPage):
    @method
    class get_investment(TableElement):
        item_xpath = '//table[@id="assets"]/tbody/tr[position() > 1]'
        head_xpath = '//table[@id="assets"]/tbody/tr[1]/td'

        col_label = u'Fonds'
        col_quantity = u'Nombre de parts'
        col_unitvalue = u'Valeur part'
        col_valuation = u'Total'
        col_portfolio_share = u'Répartition'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_quantity = MyDecimal(TableCell('quantity'))
            obj_unitvalue = MyDecimal(TableCell('unitvalue'))
            obj_valuation = MyDecimal(TableCell('valuation'))
            obj_portfolio_share = Eval(lambda x: x / 100, MyDecimal(TableCell('portfolio_share')))


class LifeHistoryPage(TransactionsPage):
    pass


class LoanHistoryPage(TransactionsPage):
    pass


class CardHistoryPage(TransactionsPage):
    pass

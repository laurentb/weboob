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


import re
from decimal import Decimal

from weboob.browser.pages import HTMLPage, LoggedPage, pagination
from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.standard import Regexp, Field, TableCell, CleanText, CleanDecimal, Eval
from weboob.browser.filters.html import Link
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


class HomePage(LoggedPage, HTMLPage):
    TYPES = {'carte': Account.TYPE_CARD, 'assurance': Account.TYPE_LIFE_INSURANCE, 'epargne': Account.TYPE_SAVINGS}
    LABEL_TYPES = [(u'Prêt personnel', Account.TYPE_LOAN)]

    @method
    class get_list(ListElement):
        item_xpath = '//div[@class="three_contenu_table" and ./div[not(contains(@class, "pp_espace_client"))]] | //div[@class="pp_espace_client"]'

        class item(ItemElement):
            klass = Account

            def obj_balance(self):
                if len(self.el.xpath('.//div[@class="catre_col_one"]/h2')) > 0:
                    balance = CleanDecimal(CleanText('.//div[@class="catre_col_one"]/h2'), replace_dots=True)(self)
                    return -balance if Field('type')(self) in (Account.TYPE_CARD, Account.TYPE_LOAN) else balance
                return Decimal('0')

            def obj_type(self):
                for label, type in self.page.LABEL_TYPES:
                    if label in Field('label')(self):
                        return type
                return self.page.TYPES.get(Regexp(Field('_link'), '\/([^-]+)')(self), Account.TYPE_UNKNOWN)

            obj_id = CleanText('.//div[@class="carte_col_leftcol"]/p') & Regexp(pattern=r'(\d+)')
            obj_label = CleanText('.//div[@class="carte_col_leftcol"]/h2')
            obj_currency = FrenchTransaction.Currency('.//div[@class="catre_col_one"]/h2')
            obj__link = Link('.//a[contains(@href, "-operations")]', default=None)


class Transaction(FrenchTransaction):
    PATTERNS = [(re.compile(r'^(?P<text>.*?) (?P<dd>\d{2})/(?P<mm>\d{2})$'), FrenchTransaction.TYPE_CARD)]


class TransactionsPage(LoggedPage, HTMLPage):
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


    @pagination
    @method
    class get_history(Transaction.TransactionsElement):
        head_xpath = u'//div[*[contains(text(), "opérations")]]/table//thead/tr/th'
        item_xpath = u'//div[*[contains(text(), "opérations")]]/table/tbody/tr'

        def next_page(self):
            next_page = Link(u'//a[contains(text(), "précédentes")]', default=None)(self)
            if next_page:
                return "/%s" % next_page

        class item(Transaction.TransactionElement):
            obj_id = None

            def obj_type(self):
                return Transaction.TYPE_CARD if len(self.el.xpath('./td')) > 3 else Transaction.TYPE_BANK

            def condition(self):
                return TableCell('raw')(self)

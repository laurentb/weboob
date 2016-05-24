# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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
from datetime import date
import re

from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.browser.elements import ListElement, TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, TableCell, Date, Env, Field, Regexp
from weboob.capabilities.bank import Account, Transaction, Investment


class InvestmentTableElement(ListElement):
    def __init__(self, *args, **kwargs):
        super(InvestmentTableElement, self).__init__(*args, **kwargs)

        self._cols = {'label': 0,
                      'unitvalue': 2,
                      'valuation': 5,
                      'quantity': 4}

    def get_colnum(self, name):
        return self._cols.get(name, None)


class LoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form(nr=0)
        form['_cm_user'] = login
        form['_cm_pwd'] = passwd
        form.submit()


class LoginErrorPage(HTMLPage):
    pass


class AvoirPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(TableElement):
        item_xpath = u'//table[@summary="Liste des échéances"]/tbody/tr'
        head_xpath = u'//table[@summary="Liste des échéances"]/thead/tr/th/text()'

        col_name = u'Plan'
        col_value = u'Evaluation en'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return u'Vous n\'avez pas d\'avoirs.' not in CleanText(TableCell('name'))(self)

            obj_id = CleanText(TableCell('name'))
            obj_label = CleanText(TableCell('name'))
            obj_balance = CleanDecimal(TableCell('value'), replace_dots=True, default=Decimal(0))
            obj_currency = CleanText(u'//table[@summary="Liste des échéances"]/thead/tr/th/small/text()')
            obj_type = Account.TYPE_PEE

    @method
    class iter_investment(InvestmentTableElement):
        item_xpath = u'(//table[@summary="Liste des échéances"]/tbody/tr)[position() < last()]'

        def parse(self, el):
            item = el.xpath(u'//table[@summary="Liste des échéances"]/tfoot/tr/td[@class="tot _c1 d _c1"]')[0]
            self.env['total'] = CleanDecimal(Regexp(CleanText('.'),
                                                    '(.*) .*'),
                                             default=1,
                                             replace_dots=True)(item)

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_vdate = date.today()  # * En réalité derniere date de valorisation connue
            obj_unitvalue = CleanDecimal(TableCell('unitvalue'), replace_dots=True)
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_quantity = CleanDecimal(TableCell('quantity'), replace_dots=True)

            def obj_portfolio_share(self):
                return Field('valuation')(self) / Env('total')(self) * 100


class OperationsFuturesPage(LoggedPage, HTMLPage):
    @method
    class get_list(TableElement):
        head_xpath = u'//table[@summary="Liste des opérations en attente"]/thead/tr/th/text()'
        item_xpath = u'//table[@summary="Liste des opérations en attente"]/tbody/tr'

        col_date = u'Date'
        col_operation = u'Opération'
        col_etat = u'Etat'
        col_montant = [u'Montant net en', re.compile(u'Montant en')]
        col_action = u'Action'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return u'Aucune opération en attente' not in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), Env('date_guesser'))
            obj_type = Transaction.TYPE_UNKNOWN
            obj_label = CleanText(TableCell('operation'))
            obj_amount = CleanDecimal(TableCell('montant'), replace_dots=True)


class OperationsTraiteesPage(LoggedPage, HTMLPage):
    @method
    class get_history(TableElement):
        head_xpath = u'//table[@summary="Liste des opérations en attente"]/thead/tr/th/text()'
        item_xpath = u'//table[@summary="Liste des opérations en attente"]/tbody/tr'

        col_date = u'Date'
        col_operation = u'Opération'
        col_montant = u'Montant net en'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return u'Aucune opération' not in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), Env('date_guesser'))
            obj_type = Transaction.TYPE_UNKNOWN
            obj_label = CleanText(TableCell('operation'))
            obj_amount = CleanDecimal(TableCell('montant'), replace_dots=True)

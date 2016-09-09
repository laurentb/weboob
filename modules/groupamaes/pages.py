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
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.standard import CleanText, CleanDecimal, TableCell, Date, Env, Regexp, Field
from weboob.capabilities.bank import Account, Transaction, Investment


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

    def iter_investment(self):
        item = self.doc.xpath(u'//table[@summary="Liste des échéances"]/tfoot/tr/td[@class="tot _c1 d _c1"]')[0]
        total = CleanDecimal(Regexp(CleanText('.'), '(.*) .*'),
                             default=1, replace_dots=True)(item)

        item_xpath = u'(//table[@summary="Liste des échéances"]/tbody/tr)[position() < last() and not(contains(./td[1]/@class, "tittot"))]'

        obj = None
        for tr in self.doc.xpath(item_xpath):
            tds = tr.xpath('./td')
            if len(tds) > 3:
                if obj is not None:
                    obj.portfolio_share = obj.valuation / total
                    yield obj

                obj = Investment()
                obj.label = CleanText('.')(tds[0])
                obj.vdate = date.today()  # * En réalité derniere date de valorisation connue
                obj.unitvalue = CleanDecimal('.', replace_dots=True)(tds[2])
                obj.valuation = CleanDecimal('.', replace_dots=True)(tds[5])
                obj.quantity = CleanDecimal('.', replace_dots=True)(tds[4])

            elif obj is not None:
                obj.quantity += CleanDecimal('.', replace_dots=True)(tds[1])
                obj.valuation += CleanDecimal('.', replace_dots=True)(tds[2])

        if obj is not None:
            obj.portfolio_share = obj.valuation / total
            yield obj


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

    NEGATIVE_AMOUNT_LABELS = [u'Retrait', u'Transfert sortant']

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

            def obj_amount(self):
                amount = CleanDecimal(TableCell('montant'), replace_dots=True)(self)
                for pattern in OperationsTraiteesPage.NEGATIVE_AMOUNT_LABELS:
                    if Field('label')(self).startswith(pattern):
                        amount = -amount
                return amount

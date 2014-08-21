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


from weboob.tools.browser2.page import HTMLPage, method, LoggedPage
from weboob.tools.browser2.elements import TableElement, ItemElement
from weboob.tools.browser2.filters import CleanText, CleanDecimal, TableCell, Date
from weboob.capabilities.bank import Account, Transaction
from weboob.tools.date import LinearDateGuesser

__all__ = ['LoginPage', 'LoginErrorPage', 'AvoirPage', 'OperationsFuturesPage', 'OperationsTraiteesPage']


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

            obj_id = CleanText(TableCell('name'))
            obj_label = CleanText(TableCell('name'))
            obj_balance = CleanDecimal(TableCell('value'), replace_dots=True)
            obj_currency = CleanText(u'//table[@summary="Liste des échéances"]/thead/tr/th/small/text()')
            obj_type = Account.TYPE_UNKNOWN


class OperationsFuturesPage(LoggedPage, HTMLPage):
    @method
    class get_list(TableElement):
        head_xpath = u'//table[@summary="Liste des opérations en attente"]/thead/tr/th/text()'
        item_xpath = u'//table[@summary="Liste des opérations en attente"]/tbody/tr'

        col_date = u'Date'
        col_operation = u'Opération'
        col_etat = u'Etat'
        col_montant = u'Montant net en'
        col_action = u'Action'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return not u'Aucune opération en attente' in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), LinearDateGuesser())
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
                return not u'Aucune opération' in CleanText(TableCell('date'))(self)

            obj_date = Date(CleanText(TableCell('date')), LinearDateGuesser())
            obj_type = Transaction.TYPE_UNKNOWN
            obj_label = CleanText(TableCell('operation'))
            obj_amount = CleanDecimal(TableCell('montant'), replace_dots=True)

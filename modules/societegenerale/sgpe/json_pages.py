# -*- coding: utf-8 -*-

# Copyright(C) 2016     Baptiste Delpey
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


from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.standard import CleanDecimal, Date, Format
from weboob.browser.filters.json import Dict
from weboob.capabilities.base import Currency
from weboob.capabilities import NotAvailable
from weboob.capabilities.bank import Account

from .pages import Transaction

class AccountsJsonPage(LoggedPage, JsonPage):
    def iter_accounts(self):
        for classeur in self.doc['donnees']['classeurs']:
            title = classeur['title']
            for compte in classeur['comptes']:
                a = Account()
                a.label = compte['libelle']
                a._id = compte['id']
                a.iban = compte['iban'].replace(' ', '')
                # id based on iban to match ids in database.
                a.id = a.iban[4:-2]
                a.type = Account.TYPE_CHECKING
                a._agency = compte['agenceGestionnaire']
                a._title = title
                yield a

    def get_error(self):
        if self.doc['commun']['statut'] == 'nok':
            return self.doc['commun']['raison']
        return None


class BalancesJsonPage(LoggedPage, JsonPage):
    def populate_balances(self, accounts):
        for account in accounts:
            acc_dict = self.doc['donnees']['compteSoldesMap'][account._id]
            account.balance = CleanDecimal(replace_dots=True).filter(acc_dict['soldeInstantane'])
            account.currency = Currency.get_currency(acc_dict['deviseSoldeComptable'])
            yield account


class HistoryJsonPage(LoggedPage, JsonPage):
    @method
    class iter_history(DictElement):
        item_xpath = 'donnees/compte/operations'

        def condition(self):
            return 'donnees' in self.page.doc

        class item(ItemElement):
            klass = Transaction

            # This is 'Date de valeur'
            obj_date = Date(Dict('dVl'), dayfirst=True)
            obj__date = Date(Dict('date', default=None), dayfirst=True, default=NotAvailable)
            obj_coming = False
            obj_raw = Transaction.Raw(Format('%s %s %s', Dict('l1'), Dict('l2'), Dict('l3')))
            # We have l4 and l5 too most of the time, but it seems to be unimportant and would make label too long.
            #tr.label = ' '.join([' '.join(transaction[l].strip().split()) for l in ['l1', 'l2', 'l3']])

            def obj_amount(self):
                return CleanDecimal(Dict('c', default=None), replace_dots=True, default=None)(self) or \
                    CleanDecimal(Dict('d'), replace_dots=True)(self)

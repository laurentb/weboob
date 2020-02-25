# -*- coding: utf-8 -*-

# Copyright(C) 2019      Vincent A
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

from weboob.browser.elements import ItemElement, method, DictElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Field,
)
from weboob.browser.pages import HTMLPage, CsvPage, LoggedPage
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Transaction
from weboob.exceptions import BrowserIncorrectPassword


MAIN_ID = '_lendosphere_'


class LoginPage(HTMLPage):
    def do_login(self, username, password):
        form = self.get_form(id='new_user')
        form['user[email]'] = username
        form['user[password]'] = password
        form.submit()

    def raise_error(self):
        msg = CleanText('//div[has-class("alert-danger")]')(self.doc)
        if 'Votre email ou mot de passe est incorrect' in msg:
            raise BrowserIncorrectPassword(msg)
        assert False, 'unhandled error %r' % msg


class SummaryPage(LoggedPage, HTMLPage):
    pass


class ProfilePage(LoggedPage, HTMLPage):
    pass


class ComingProjectPage(LoggedPage, HTMLPage):
    def iter_projects(self):
        return [value for value in self.doc.xpath('//select[@id="offer"]/option/@value') if value != '*']


class ComingPage(LoggedPage, CsvPage):
    HEADER = 1

    @method
    class iter_transactions(DictElement):
        class item(ItemElement):
            klass = Transaction

            obj_type = Transaction.TYPE_BANK
            obj_raw = Dict('Projet')
            obj_date = Date(Dict('Date'), dayfirst=True)

            obj_gross_amount = CleanDecimal.SI(Dict('Capital rembourse'))
            obj_amount = CleanDecimal.SI(Dict('Montant brut'))
            obj_commission = CleanDecimal.SI(Dict('Interets'))

            obj__amount_left = CleanDecimal.SI(Dict('Capital restant du'))


class GSummaryPage(LoggedPage, HTMLPage):
    @method
    class get_account(ItemElement):
        klass = Account

        obj_id = MAIN_ID
        obj_currency = 'EUR'
        obj_number = NotAvailable
        obj_type = Account.TYPE_MARKET
        obj_label = 'Lendosphere'

        obj__liquidities = CleanDecimal.French('//div[div[@class="subtitle"][contains(text(),"Somme disponible")]]/div[@class="amount"]')
        obj__invested = CleanDecimal.French('//tr[td[contains(text(),"Echéances restantes")]]/td[last()]')

        def obj_balance(self):
            return Field('_liquidities')(self) + Field('_invested')(self)

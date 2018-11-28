# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from weboob.browser.elements import ListElement, ItemElement, method, TableElement
from weboob.browser.filters.html import TableCell, Link, Attr
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Slugify, Date, Field, Format,
)
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import Account, Transaction, Investment
from weboob.capabilities.profile import Profile
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import urljoin


MAIN_ID = '_bolden_'

class LoginPage(HTMLPage):
    def do_login(self, username, password):
        form = self.get_form(id='loginform')
        form['Email'] = username
        form['Password'] = password
        form.submit()

    def check_error(self):
        msg = CleanText('//div[has-class("validation-summary-errors")]')(self.doc)
        if 'Tentative de connexion invalide' in msg:
            raise BrowserIncorrectPassword(msg)


class HomeLendPage(LoggedPage, HTMLPage):
    pass


class PortfolioPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        class item(ItemElement):
            klass = Account

            obj_id = MAIN_ID
            obj_label = 'Compte Bolden'
            obj_type = Account.TYPE_MARKET
            obj_currency = 'EUR'
            obj_balance = CleanDecimal('//div[p[has-class("investor-state") and contains(text(),"Total compte Bolden :")]]/p[has-class("investor-status")]', replace_dots=True)
            obj_valuation_diff = CleanDecimal('//p[has-class("rent-amount strong dashboard-text")]', replace_dots=True)

    @method
    class iter_investments(TableElement):
        head_xpath = '//div[@class="tab-wallet"]/table/thead//td'

        col_label = 'Emprunteur'
        col_valuation = 'Capital restant dû'
        col_doc = 'Contrat'
        col_diff = 'Intérêts perçus'

        item_xpath = '//div[@class="tab-wallet"]/table/tbody/tr'

        class item(ItemElement):
            klass = Investment

            obj_label = CleanText(TableCell('label'))
            obj_id = Slugify(Field('label'))
            obj_valuation = CleanDecimal(TableCell('valuation'), replace_dots=True)
            obj_diff = CleanDecimal(TableCell('diff'), replace_dots=True)
            obj_code = NotAvailable
            obj_code_type = NotAvailable

            def condition(self):
                # Investments without valuation are expired.
                return CleanDecimal(TableCell('valuation'))(self)

            def obj__docurl(self):
                return urljoin(self.page.url, Link('.//a')(TableCell('doc')(self)[0]))

    def get_liquidity(self):
        return CleanDecimal('//div[p[contains(text(), "Fonds disponibles")]]/p[@class="investor-status strong"]', replace_dots=True)(self.doc)


class OperationsPage(LoggedPage, HTMLPage):
    @method
    class iter_history(TableElement):
        head_xpath = '//div[@class="tab-wallet"]/table/thead//td'

        col_date = 'Date'
        col_label = 'Opération'
        col_amount = 'Montant'

        item_xpath = '//div[@class="tab-wallet"]/table/tbody/tr'

        class item(ItemElement):
            klass = Transaction

            def condition(self):
                return not Field('label')(self).startswith('dont ')

            obj_label = CleanText(TableCell('label'))

            def obj_amount(self):
                v = CleanDecimal(TableCell('amount'), replace_dots=True)(self)
                if Field('label')(self).startswith('Investissement'):
                    v = -v
                return v

            obj_date = Date(CleanText(TableCell('date')), dayfirst=True, default=None)


class ProfilePage(LoggedPage, HTMLPage):
    @method
    class get_profile(ItemElement):
        klass = Profile

        obj_name = Format(
            '%s %s',
            Attr('//input[@id="SubModel_FirstName"]', 'value'),
            Attr('//input[@id="SubModel_LastName"]', 'value'),
        )
        obj_phone = Attr('//input[@id="SubModel_Phone"]', 'value')
        obj_address = Format(
            '%s %s %s %s %s',
            Attr('//input[@id="SubModel_Address_Street"]', 'value'),
            Attr('//input[@id="SubModel_Address_Suplement"]', 'value'),
            Attr('//input[@id="SubModel_Address_PostalCode"]', 'value'),
            Attr('//input[@id="SubModel_Address_City"]', 'value'),
            CleanText('//select[@id="SubModel_Address_Country"]/option[@selected]'),
        )

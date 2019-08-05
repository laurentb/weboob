# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

import sys
from datetime import date

from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, MapIn, Field,
    Currency, Regexp, Format, Eval,
)
from weboob.browser.filters.json import Dict
from weboob.browser.filters.html import Attr, Link
from weboob.capabilities.bank import Account, Transaction
from weboob.browser.elements import (
    DictElement, ListElement, ItemElement, method,
)
from weboob.capabilities.base import NotAvailable
from weboob.tools.compat import unicode
from weboob.browser.pages import HTMLPage, LoggedPage, CsvPage


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(id='fm1')
        form['username'] = username
        form['password'] = password
        form.submit()

    def get_error_message(self):
        return CleanText('//div[@class="alert alert-danger"]')(self.doc)

    def is_logged(self):
        return CleanText('//div[@id="successTextBloc"]/h2')(self.doc) == 'Log In Successful'


class DashboardPage(LoggedPage, HTMLPage):
    @method
    class iter_accounts(ListElement):
        item_xpath = '//div[@class="container header_desktop"]//a[@class="carte"]'

        class item(ItemElement):
            klass = Account

            def condition(self):
                return CleanText('./span[@class="lanNavSel_succes_carte"]')(self)

            obj_url = Link('.')

    @method
    class fill_account(ItemElement):
        obj_type = Account.TYPE_CARD
        # most xpaths in the module are long and strict because the html contains multiple versions of
        # the site that are displayed or not via js depending on the size of the screen
        # they are not displayed but still present, so the xpaths can catch them
        # and we want to avoid that
        obj_number = CleanText('//div[@class="row bnp_carte_dashboard_one"]//span[@id="carte_dashboard_numero_compte"]')
        obj_id = Field('number')

        obj_label = Format(
            '%s %s',
            CleanText('//div[@class="row bnp_carte_dashboard_one"]//span[@id="carte_dashboard_title"]'),
            CleanText('//div[contains(@class,"hidden-xs")]//div[contains(@class,"bnp_info_general_one")]//ul[@class="list-group bnp_information"]/li[2]')
        )

        # TODO Handle 'Fin du mois'
        obj_paydate = Date(
            Regexp(
                CleanText('//div[@class="row prelevement"]/div[@class="prelevement-box"][1]/span[@class="prelevement_le"]'),
                r'(\d{2}/\d{2}/\d{4})',
                default=NotAvailable
            ),
            dayfirst=True,
            default=NotAvailable
        )

        obj_currency = Currency(
            CleanText('//div[@class="plafondStyle"]//p[@class="paiement_content_color"]')
        )

        obj_coming = Eval(
            lambda x, y: x + y,
            CleanDecimal.French('//div[contains(@class, "hidden-xs")]//div[contains(@class, "cumul_content_dashboard")]//span[@class = "content_paiement"]', default=NotAvailable),
            CleanDecimal.French('//div[contains(@class, "hidden-xs")]//div[contains(@class, "cumul_content_dashboard")]//span[@class = "content_retrait"]', default=NotAvailable)
        )


class TransactionPage(LoggedPage, HTMLPage):
    def get_instance_id(self):
        return Regexp(
            Attr('//span[contains(@id,"p_Phenix_Transactions_Portlet_INSTANCE_")]', 'id'),
            r'INSTANCE_([^_]*)'
        )(self.doc)


class TransactionCSV(LoggedPage, CsvPage):
    HEADER = 9

    FMTPARAMS = {'delimiter': ';'}

    def build_doc(self, content):
        # Dict splits keys on '/' it is intended behaviour because it's primary
        # use is with json files, but it means I have to replace '/' here
        delimiter = self.FMTPARAMS.get('delimiter')
        if sys.version_info.major == 2 and delimiter and isinstance(delimiter, unicode):
            self.FMTPARAMS['delimiter'] = delimiter.encode('utf-8')
        content = content.replace(b'/', b'-')
        return super(TransactionCSV, self).build_doc(content)

    @method
    class iter_history(DictElement):
        class item(ItemElement):
            klass = Transaction

            TRANSACTION_TYPES = {
                'FACTURE CB': Transaction.TYPE_CARD,
                'RETRAIT CB': Transaction.TYPE_WITHDRAWAL,
            }

            obj_label = CleanText(Dict('Raison sociale commerçant'))
            obj_amount = CleanDecimal.French(Dict('Montant EUR'))
            obj_original_currency = CleanText(Dict("Devise d'origine"))
            obj_rdate = Date(CleanText(Dict("Date d'opération")), dayfirst=True)
            obj_date = Date(CleanText(Dict('Date débit-crédit')), dayfirst=True)

            obj_type = MapIn(
                CleanText(Dict('Libellé opération')),
                TRANSACTION_TYPES
            )

            def obj_commission(self):
                commission = CleanDecimal.French(Dict('Commission'))(self)
                if commission != 0:  # We don't want to return null commissions
                    return commission
                return NotAvailable

            def obj_original_amount(self):
                original_amount = CleanDecimal.French(Dict("Montant d'origine"))(self)
                if original_amount != 0:  # We don't want to return null original_amounts
                    return original_amount
                return NotAvailable

            def obj__coming(self):
                return Field('date')(self) >= date.today()


class PasswordExpiredPage(LoggedPage, HTMLPage):
    def get_error_message(self):
        return CleanText('//span[@class="messageWarning"]')(self.doc)

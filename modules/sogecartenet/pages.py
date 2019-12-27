# -*- coding: utf-8 -*-

# Copyright(C) 2015 Budget Insight
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

from weboob.browser.pages import LoggedPage
from weboob.browser.elements import ItemElement, ListElement, TableElement, method
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Format, Currency,
)
from weboob.browser.filters.html import Attr, TableCell
from weboob.capabilities.bank import Account, Transaction
from weboob.browser.selenium import SeleniumPage, VisibleXPath, AllCondition

from .ent_pages import LoginPage as _LoginPage


class LoginPage(_LoginPage):
    def get_error(self):
        return (
            CleanText('//div[@id="labelQuestion"]')(self.doc)
            or CleanText('//h1[contains(@class, "Notification-caption")]')(self.doc)
        )


class PreLoginPage(SeleniumPage):
    is_here = VisibleXPath('//div[span[span[div[contains(text(), "Accès Titulaire")]]]]')

    def go_login(self):
        el = self.driver.find_element_by_xpath('//div[span[span[div[contains(text(), "Accès Titulaire")]]]]')
        el.click()


class AccountsPage(LoggedPage, SeleniumPage):
    is_here = AllCondition(
        VisibleXPath('//div[contains(text(), "Capacités de paiement et retrait")]'),
        VisibleXPath('//div[@id="MESINFOS_HEADER_PANEL_CARTE"]'),
        VisibleXPath('//div[contains(text(), "Mes coordonnées bancaires")]'),
    )

    @method
    class iter_accounts(ListElement):
        class item(ItemElement):
            klass = Account

            obj_id = obj_number = Format(
                '%s_%s',
                Attr('//div[span[contains(text(), "Identifiant prestation")]]/following-sibling::input', 'value'),
                Attr('//div[span[contains(text(), "Numéro de la carte")]]/following-sibling::input', 'value'),
            )
            obj_label = CleanText('//div[@class="v-slot"]/div[contains(@class, "v-label-undef-w")]')

            obj_iban = CleanText(Attr('//div[span[contains(text(), "IBAN")]]/following-sibling::input', 'value'), replace=[(' ', '')])

            obj_balance = 0
            obj_type = Account.TYPE_CARD


class HistoryPage(LoggedPage, SeleniumPage):
    is_here = AllCondition(
        VisibleXPath('//thead[@role="rowgroup"]'),
        VisibleXPath('//tbody[@role="rowgroup"]'),
        VisibleXPath('//table[@role="presentation"]//td'),
        VisibleXPath('//div[@role="tabpanel"]'),
    )

    @method
    class fill_account_details(ItemElement):
        def obj_coming(self):
            # There might be multiple coming values (if the transactions are differed
            # for more than 1 month). So we take the sum of all the coming values available
            # in the table.
            return sum(map(
                CleanDecimal.SI().filter,
                self.page.doc.xpath('//tbody[@role="rowgroup"]/tr/td[contains(@class, "montant")]')
            ))

    def go_coming_tab(self):
        el = self.driver.find_element_by_xpath('//div[contains(text(), "Prélèvements à venir")]')
        el.click()

        self.browser.wait_xpath_visible('//tbody[@role="rowgroup"]/tr')

    def go_history_tab(self):
        el = self.driver.find_element_by_xpath('//table[@role="presentation"]//div[contains(text(), "Consultation")]')
        el.click()

        self.browser.wait_xpath_visible('//tbody[@role="rowgroup"]/tr')

    def get_currency(self):
        return Currency('//div[div[contains(text(), "Montant des opérations")]]/following-sibling::div[contains(@class, "v-slot")]/div')(self.doc)

    def wait_history_xpaths_visible(self):
        self.browser.wait_until(AllCondition(
            VisibleXPath('//div[contains(@class, "debitDate")]'),
            VisibleXPath('//div[div[contains(text(), "Montant des opérations")]]/following-sibling::div[@class="v-slot"]'),
            VisibleXPath('//thead[@role="rowgroup"]'),
            VisibleXPath('//tbody[@role="rowgroup"]'),
        ))

    def select_first_date_history(self):
        self.go_history_tab()
        el = self.driver.find_element_by_xpath('//div[div[contains(text(), "Arrêté du")]]/following-sibling::div//input')
        el.click()

        self.browser.wait_xpath_visible('//div[contains(@class, "suggestmenu")]//td')

        el = self.driver.find_element_by_xpath('//div[contains(@class, "suggestmenu")]//tr[1]')
        el.click()

        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')
        # Wait for the data to refresh
        self.wait_history_xpaths_visible()

    def go_next_page(self):
        el = self.driver.find_element_by_xpath('//div[div[contains(text(), "Arrêté du")]]/following-sibling::div//input')
        el.click()

        self.browser.wait_xpath_visible('//div[contains(@class, "suggestmenu")]//td')
        # If we are not on the last item of the list already, there is still another page
        if self.doc.xpath('//div[contains(@class, "suggestmenu")]//tr[td[contains(@class, "selected")]]/following-sibling::tr/td'):

            el = self.driver.find_element_by_xpath('//div[contains(@class, "suggestmenu")]//tr[td[contains(@class, "selected")]]/following-sibling::tr/td[1]')
            el.click()

            self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')
            # Wait for the data to refresh
            self.wait_history_xpaths_visible()
            return True
        return False

    @method
    class iter_history(TableElement):
        head_xpath = '//thead[@role="rowgroup"]/tr/th'
        item_xpath = '//tbody[@role="rowgroup"]/tr'

        col_label = 'Libellé'
        col_amount = 'Montant transaction'
        col_rdate = 'Date achat'

        class item(ItemElement):
            klass = Transaction

            obj_date = Date(CleanText('//div[div[contains(text(), "Date de prélèvement")]]/following-sibling::div/div'), dayfirst=True)
            obj_rdate = Date(CleanText(TableCell('rdate')), dayfirst=True)
            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal.SI(TableCell('amount'))
            obj_type = Transaction.TYPE_CARD

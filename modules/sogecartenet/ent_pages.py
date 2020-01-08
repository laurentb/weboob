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

import time
import re

from selenium.webdriver.common.keys import Keys

from weboob.capabilities.bank import Account, Transaction
from weboob.browser.pages import LoggedPage
from weboob.browser.filters.standard import (
    CleanText, CleanDecimal, Date, Format,
    Env,
)
from weboob.browser.filters.html import TableCell
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.selenium import SeleniumPage, VisibleXPath, AllCondition, AnyCondition


class LoginPage(SeleniumPage):
    is_here = AllCondition(
        VisibleXPath('//div[span[contains(text(), "Identifiant")]]/following-sibling::input'),
        VisibleXPath('//div[span[contains(text(), "Mot de passe")]]/following-sibling::input'),
        VisibleXPath('//div[span[span[contains(text(), "Valider")]]]'),
    )

    def login(self, username, password):
        el = self.driver.find_element_by_xpath('//div[span[contains(text(), "Identifiant")]]/following-sibling::input')
        el.click()
        el.send_keys(username)

        el = self.driver.find_element_by_xpath('//div[span[contains(text(), "Mot de passe")]]/following-sibling::input')
        el.click()
        el.send_keys(password)

        el.send_keys(Keys.RETURN)

    def get_error(self):
        return CleanText('//h1[contains(@class, "Notification-caption")]')(self.doc)


class AccueilPage(LoggedPage, SeleniumPage):
    is_here = VisibleXPath('//div[@id="Menu-responsive"]')


class AccountsPage(LoggedPage, SeleniumPage):
    is_here = AllCondition(
        VisibleXPath('//div[contains(@class, "margin-donwload-btn")]'),
        VisibleXPath('//thead[contains(@class, "v-grid-header")]'),
        VisibleXPath('//tbody[contains(@class, "v-grid-body")]'),
    )

    def go_history(self):
        el = self.driver.find_element_by_xpath('//span[contains(text(), "Dépenses entreprise")]')
        el.click()

    def select_account(self, account_label):
        el = self.driver.find_element_by_xpath('//td[contains(text(), "%s")]/preceding-sibling::td[div[div]]//div[contains(@class, "v-button")]' % account_label)
        el.click()

    @method
    class iter_accounts(TableElement):
        head_xpath = '//table[@role="grid"]/thead[contains(@class, "v-grid-header")]/tr/th/div[1]'
        item_xpath = '//table[@role="grid"]/tbody[contains(@class, "v-grid-body")]/tr'

        col_label = 'Titulaire'
        col_card_number = 'Numéro de carte'
        col_service_number = 'Numéro de prestation'

        class item(ItemElement):
            klass = Account

            # TableCell('service_number') alone is not enough because a person with the
            # same service_number might have multiple cards.
            # And a card number can be associated to multiple persons.
            obj_id = obj_number = Format(
                '%s_%s',
                CleanText(TableCell('service_number')),
                CleanText(TableCell('card_number')),
            )
            obj_label = CleanText(TableCell('label'))
            obj_currency = 'EUR'
            obj_type = Account.TYPE_CARD


class HistoryPage(LoggedPage, SeleniumPage):
    is_here = AllCondition(
        VisibleXPath('//div[contains(text(), "Recherche opérations")]'),
        VisibleXPath('//div[contains(text(), "Synthèse entreprise")]'),
    )

    def go_transactions_list_tab(self):
        el = self.driver.find_element_by_xpath('//div[contains(text(), "Recherche opérations")]')
        el.click()

        self.browser.wait_xpath_clickable('//div[contains(@class, "v-widget")][div[div[@id="BTN_SEARCH"]]]')

    def fetch_date_list(self):
        self.go_transactions_list_tab()

        # Both date inputs have the same date list
        el = self.driver.find_element_by_xpath('//input[contains(@placeholder, "À la date d\'arrêté")]')
        el.click()

        self.browser.wait_xpath_visible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # The 'select' input has multiple pages. To be able to see the older
        # dates, the website requires you to scroll/click because
        # the dates are added/removed dynamically in the input.
        # On the first page we have 1 year worth of transactions, which
        # is enough. So we retrieve the deferred dates only for the last year.
        # Dates are ordered from newest to oldest in the xpath
        date_list = list(map(
            Date(dayfirst=True).filter,
            CleanText('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]//div[contains(@class, "suggestmenu")]//span')(self.doc).split()
        ))

        # Click on the element again to restore the status of input
        el.click()
        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')
        return date_list

    # Only used for getting the sum of all comings for an account
    # (currently not used, see browser.py/iter_accounts)
    def get_transactions_amount_sum(self):
        return sum(map(
            CleanDecimal.SI().filter,
            self.doc.xpath('//tbody[@role="rowgroup"]/tr/td[last()]')
        ))

    # Only used for getting the sum of all comings for an account
    # (currently not used, see browser.py/iter_accounts)
    def display_all_comings(self, date_list, today):
        self.go_transactions_list_tab()

        # Click the 'from date' select input
        el = self.driver.find_element_by_xpath('//input[contains(@placeholder, "De la date d\'arrêté")]')
        el.click()
        self.browser.wait_xpath_visible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Search for the first date that is right after today's date and click it.
        for date_choice in reversed(date_list):
            if date_choice > today:
                el = self.driver.find_element_by_xpath('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]//div[contains(@class, "suggestmenu")]//span[text()="%s"]' % date_choice.strftime('%d/%m/%Y'))
                el.click()
                break

        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Click the 'to date' select input
        el = self.driver.find_element_by_xpath('//input[contains(@placeholder, "À la date d\'arrêté")]')
        el.click()
        self.browser.wait_xpath_visible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Select the first date (which is the newest one)
        el = self.driver.find_element_by_xpath('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]//div[contains(@class, "suggestmenu")]//tr[1]')
        el.click()

        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        self.driver.execute_script("document.getElementById('BTN_SEARCH').click()")

        self.browser.wait_until(AnyCondition(
            VisibleXPath('//table[@role="grid"]'),  # the normal grid with the data
            VisibleXPath('//p[contains(text(), "Aucune opération")]'),  # no grid because no data
        ))

        if not CleanText('//p[contains(text(), "Aucune opération")]')(self.doc):
            # Data might not be refreshed immediately if we already selected
            # an account earlier. The xpath is available but the data
            # inside the table might be from a previous account we selected
            # previously.
            time.sleep(1)

    def display_transactions(self, date_choice):
        self.go_transactions_list_tab()

        # Click the 'from date' select input
        el = self.driver.find_element_by_xpath('//input[contains(@placeholder, "De la date d\'arrêté")]')
        el.click()
        self.browser.wait_xpath_visible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Click the date element in the list
        el = self.driver.find_element_by_xpath('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]//div[contains(@class, "suggestmenu")]//span[text()="%s"]' % date_choice.strftime('%d/%m/%Y'))
        el.click()

        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Click the 'to date' select input
        el = self.driver.find_element_by_xpath('//input[contains(@placeholder, "À la date d\'arrêté")]')
        el.click()
        self.browser.wait_xpath_visible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        # Click the date element in the list
        el = self.driver.find_element_by_xpath('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]//div[contains(@class, "suggestmenu")]//span[text()="%s"]' % date_choice.strftime('%d/%m/%Y'))
        el.click()

        self.browser.wait_xpath_invisible('//div[@id="VAADIN_COMBOBOX_OPTIONLIST"]')

        self.driver.execute_script("document.getElementById('BTN_SEARCH').click()")

        self.browser.wait_until(AnyCondition(
            VisibleXPath('//table[@role="grid"]'),  # the normal grid with the data
            VisibleXPath('//p[contains(text(), "Aucune opération")]'),  # no grid because no data
        ))

        if not CleanText('//p[contains(text(), "Aucune opération")]')(self.doc):
            # Data might not be refreshed immediately if we already selected
            # an account earlier. The xpath is available but the data
            # inside the table might be from a previous account we selected
            # previously.
            time.sleep(1)

    @method
    class iter_history(TableElement):
        head_xpath = '//table[@role="grid"]/thead/tr/th/div[1]'
        item_xpath = '//table[@role="grid"]/tbody/tr'

        col_label = 'Raison sociale'
        col_amount = re.compile('Montant')
        col_date = 'Date opération'

        class item(ItemElement):
            klass = Transaction

            obj_label = CleanText(TableCell('label'))
            obj_amount = CleanDecimal.SI(TableCell('amount'))
            obj_date = Env('date')
            obj_rdate = Date(CleanText(TableCell('date')), dayfirst=True)
            obj_type = Transaction.TYPE_CARD

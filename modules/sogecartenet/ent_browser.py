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

from datetime import date

from weboob.browser import URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.browser.selenium import (
    SeleniumBrowser, webdriver, AnyCondition, VisibleXPath, IsHereCondition,
)

from .ent_pages import (
    LoginPage, AccueilPage, AccountsPage, HistoryPage,
)


class SogecarteEntrepriseBrowser(SeleniumBrowser):
    BASEURL = 'https://www.sogecartenet.fr'

    # Required so the input for the transaction history date list do not overlap vertically
    WINDOW_SIZE = (1920, 1080)

    # False for debug / True for production
    HEADLESS = True

    DRIVER = webdriver.Chrome

    login = URL(r'/gestionnaire-ihm/SOCGEN/FRA$', LoginPage)
    accueil = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!ACCUEIL', AccueilPage)
    account_list = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!GESTION_PARC_CARTES', AccountsPage)
    history = URL(r'/gestionnaire-ihm/SOCGEN/FRA#!DEPENSES_ENTREPRISE', HistoryPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        kwargs['responses_dirname'] = '/tmp/selenium'
        super(SogecarteEntrepriseBrowser, self).__init__(*args, **kwargs)

        # The parsing using selenium is really long, this will avoid
        # errors if the day changes while parsing.
        self.today = date.today()
        self.date_list = []

    def do_login(self):
        self.login.go()
        self.wait_until_is_here(self.login)

        self.page.login(self.username, self.password)

        self.wait_until(AnyCondition(
            IsHereCondition(self.accueil),
            VisibleXPath('//div[contains(@class, "Notification-error-message")]'),
        ))

        if not self.accueil.is_here():
            assert self.login.is_here(), 'We landed on an unknown page'
            error = self.page.get_error()
            if any((
                'Votre compte a été désactivé' in error,
                'Votre compte est bloqué' in error,
            )):
                raise ActionNeeded(error)
            raise BrowserIncorrectPassword(error)

        self._update_cookie_time()

    def _update_cookie_time(self):
        # This cookie needs to be updated with a better time
        # (here we put 1 day) otherwise we might get disconnected while
        # parsing informations.
        self.driver.execute_script("""
        var exdate = new Date();
        exdate.setDate(exdate.getDate() + 1);
        document.cookie = encodeURIComponent('POPUP_COOKIE') + "=" + encodeURIComponent('CHECKED') + "; expires="+exdate.toUTCString();
        """)

    @need_login
    def iter_accounts(self):
        self.account_list.stay_or_go()
        self.wait_until_is_here(self.account_list)

        return self.page.iter_accounts()

        # The following code is to retrieve the coming value
        # for each account. It is currently not used, because
        # it takes a LOT of time to do that since there usually is
        # a lot of cards on one account, but might be useful later
        # so we do not delete it.
        '''for acc in account_list:
            self.select_account(acc.label)

            self.history.go()
            self.wait_until_is_here(self.history)

            if not self.date_list:
                self.date_list = self.page.fetch_date_list()

            self.page.display_all_comings(self.date_list, self.today)
            acc.coming = self.page.get_transactions_amount_sum()
            yield acc'''

    def select_account(self, account_label):
        self.account_list.go()
        self.wait_until_is_here(self.account_list)

        self.page.select_account(account_label)

    def iter_transactions(self, account, coming=False):
        self.select_account(account.label)

        self.history.go()
        self.wait_until_is_here(self.history)

        if not self.date_list:
            self.date_list = self.page.fetch_date_list()

        for date_choice in self.date_list:
            if (coming and date_choice >= self.today) or (not coming and date_choice < self.today):
                self.page.display_transactions(date_choice)
                for tr in sorted_transactions(self.page.iter_history(date=date_choice)):
                    yield tr

    @need_login
    def iter_history(self, account):
        return self.iter_transactions(account)

    @need_login
    def iter_coming(self, account):
        return self.iter_transactions(account, coming=True)

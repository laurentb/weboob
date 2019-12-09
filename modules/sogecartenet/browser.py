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

from datetime import date

from weboob.browser import URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.selenium import (
    SeleniumBrowser, webdriver, AnyCondition, IsHereCondition,
    VisibleXPath,
)

from .ent_pages import AccueilPage
from .pages import LoginPage, PreLoginPage, AccountsPage, HistoryPage


class SogecarteTitulaireBrowser(SeleniumBrowser):
    BASEURL = 'https://www.sogecartenet.fr'

    # False for debug / True for production
    HEADLESS = True

    DRIVER = webdriver.Chrome

    pre_login = URL(r'/ih3m-ihm/SOCGEN/FRA', PreLoginPage)
    login = URL(r'/ih3m-ihm/SOCGEN/FRA', LoginPage)
    accueil = URL(r'/ih3m-ihm/SOCGEN/FRA#!ACCUEIL', AccueilPage)
    accounts = URL(r'/ih3m-ihm/SOCGEN/FRA#!INFORMATION', AccountsPage)
    history = URL(r'/ih3m-ihm/SOCGEN/FRA#!COMPTE', HistoryPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        super(SogecarteTitulaireBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.pre_login.go()
        self.wait_until_is_here(self.pre_login)

        self.page.go_login()
        self.wait_until_is_here(self.login)
        self.page.login(self.username, self.password)

        self.wait_until(AnyCondition(
            IsHereCondition(self.accueil),
            VisibleXPath('//div[@id="labelQuestion"]'),
        ))

        if not self.accueil.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def iter_accounts(self):
        self.accounts.go()
        self.wait_until_is_here(self.accounts)

        # TODO implement pagination when we have a connection
        # with multiple accounts.
        accounts = list(self.page.iter_accounts())

        self.history.go()
        self.wait_until_is_here(self.history)

        self.page.go_history_tab()
        currency = self.page.get_currency()
        self.page.go_coming_tab()

        for acc in accounts:
            acc.currency = currency
            self.page.fill_account_details(obj=acc)
            yield acc

    @need_login
    def iter_transactions(self, account, coming=False):
        self.history.stay_or_go()
        self.wait_until_is_here(self.history)

        self.page.select_first_date_history()

        today = date.today()
        # 1 page = 1 month
        page_count = 0
        has_next_page = True
        # Limit number of pages to avoid infinite loops
        while has_next_page and page_count < 36:
            for tr in self.page.iter_history():
                if tr.date <= today and not coming:
                    yield tr
                elif tr.date > today and coming:
                    yield tr
                elif tr.date <= today and coming:
                    # Transactions are always ordered by most recent, so if
                    # we passed today's date we can stop checking for more
                    return
            page_count += 1
            has_next_page = self.page.go_next_page()

    @need_login
    def iter_history(self, account):
        return self.iter_transactions(account)

    @need_login
    def iter_coming(self, account):
        return self.iter_transactions(account, coming=True)

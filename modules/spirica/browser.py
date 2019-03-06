# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ClientError

from .pages import LoginPage, AccountsPage, DetailsPage, MaintenancePage


class SpiricaBrowser(LoginBrowser):
    TIMEOUT = 180

    login = URL('/securite/login.xhtml', LoginPage)
    accounts = URL('/sylvea/client/synthese.xhtml', AccountsPage)
    details = URL('/sylvea/contrat/consultationContratEpargne.xhtml', DetailsPage)
    maintenance = URL('/maintenance.html', MaintenancePage)

    def __init__(self, website, *args, **kwargs):
        super(SpiricaBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.cache = {}
        self.cache['invs'] = {}
        self.transaction_page = None

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            error = self.page.get_error()
            raise BrowserIncorrectPassword(error)

    def get_subscription_list(self):
        return iter([])

    @need_login
    def iter_accounts(self):
        return self.accounts.go().iter_accounts()

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            # Get form to show PRM
            self.location(account.url)
            self.page.goto_unitprice()
            invs = [i for i in self.page.iter_investment()]
            invs_pm = [i for i in self.page.iter_pm_investment()]
            self.fill_from_list(invs, invs_pm)
            self.cache['invs'][account.id] = invs
        return self.cache['invs'][account.id]

    def check_if_logged_in(self, url):
        if self.login.is_here():
            self.logger.warning('We were logged out during iter_history, proceed to re-login.')
            self.do_login()
            self.location(url)
            self.page.go_historytab()
            # Store new transaction_page after login:
            self.transaction_page = self.page

    @need_login
    def get_transactions_with_investments(self, max_count, url):
        transactions = []
        for index, transaction in enumerate(self.page.iter_history()):
            self.check_if_logged_in(url)
            if index < max_count:
                try:
                    self.transaction_page.go_investments_form(transaction._index)
                except ClientError as e:
                    self.logger.warning(e)
                # Check if we are logged out
                if self.login.is_here():
                    self.check_if_logged_in(url)
                if self.details.is_here():
                    transaction.investments = []
                    for inv in self.page.iter_transactions_investments():
                        # Only keep investments that have at least a label and a valuation:
                        if inv.label and inv.valuation:
                            transaction.investments.append(inv)
            transactions.append(transaction)
        return transactions

    @need_login
    def iter_history(self, account):
        self.location(account.url)
        self.page.go_historytab()
        self.transaction_page = self.page

        # Determining the number of transaction pages:
        total_pages = int(self.page.count_transactions()) // 100

        # Scraping transactions with their investments for the 20 first transactions.
        # Sometimes go_historyall fails so we go back to the accounts page and retry.
        if self.transaction_page.go_historyall(page_number=0):
            for tr in self.get_transactions_with_investments(20, account.url):
                yield tr
        else:
            self.logger.warning('The first go_historyall() failed, go back to account details and retry.')
            self.location(account.url)
            self.page.go_historytab()
            self.transaction_page = self.page
            if self.transaction_page.go_historyall(page_number=0):
                for tr in self.get_transactions_with_investments(20, account.url):
                    yield tr

        # Scraping other transaction pages without their investments:
        for page_number in range(1, total_pages + 1):
            self.check_if_logged_in(account.url)
            if not self.transaction_page.go_historyall(page_number):
                self.logger.warning('The first go_historyall() failed, go back to account details and retry.')
                self.location(account.url)
                self.page.go_historytab()
                self.transaction_page = self.page
                if not self.transaction_page.go_historyall(page_number):
                    self.logger.warning('The go_historyall() failed twice, these transactions will be skipped.')
                    continue
            for transaction in self.page.iter_history():
                yield transaction

    def fill_from_list(self, invs, objects_list):
        matching_fields = ['code', 'unitvalue', 'label', '_gestion_type']
        for inv in invs:
            # Some investments don't have PRM
            if inv._invest_type != 'Fonds en euros':
                obj_from_list = [o for o in objects_list if all(getattr(o, field) == getattr(inv, field) for field in matching_fields)]
                assert len(obj_from_list) == 1
                for name, field_value in obj_from_list[0].iter_fields():
                    if field_value:
                        setattr(inv, name, field_value)

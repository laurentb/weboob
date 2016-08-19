# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, DetailsPage, MaintenancePage


class SpiricaBrowser(LoginBrowser):
    TIMEOUT = 60
    login = URL('/securite/login.xhtml', LoginPage)
    accounts = URL('/sylvea/client/synthese.xhtml', AccountsPage)
    details = URL('/sylvea/contrat/consultationContratEpargne.xhtml', DetailsPage)
    maintenance = URL('/maintenance.html', MaintenancePage)

    def __init__(self, website, username, password, *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.username = username
        self.password = password

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    def get_subscription_list(self):
        return iter([])

    @need_login
    def iter_accounts(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def iter_investment(self, account):
        # Get form to show PRM
        form = self.location(account._link).page.get_investment_form()
        return self.location(form.url, data=dict(form)).page.iter_investment()

    @need_login
    def iter_history(self, account):
        # Get form to go to History's tab
        form = self.location(account._link).page.get_historytab_form()
        # Get form to show all transactions
        form = self.location(form.url, data=dict(form)).page.get_historyallpages_form()
        if form:
            self.location(form.url, data=dict(form))
        # Get forms to expand details of all transactions
        for form in self.page.get_historyexpandall_form():
            self.location(form.url, data=dict(form))
        # Get all transactions
        self.skipped = []
        transactions = []
        for t in self.page.iter_history():
            transactions.append(t)
        for t in self.page.iter_history_skipped():
            transactions.append(t)
        return iter(sorted(transactions, key=lambda t: t.date, reverse=True))

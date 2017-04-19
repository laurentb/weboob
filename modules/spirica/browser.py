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

    def __init__(self, website, *args, **kwargs):
        super(SpiricaBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = website
        self.cache = {}
        self.cache['invs'] = {}
        self.cache['trs'] = {}

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            error = self.page.get_error()
            raise BrowserIncorrectPassword(error)

    def get_subscription_list(self):
        return iter([])

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.cache['accs'] = [a for a in self.accounts.stay_or_go().iter_accounts()]
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            # Get form to show PRM
            form = self.location(account.url).page.get_investment_form()
            invs = [i for i in self.location(form.url, data=dict(form)).page.iter_investment()]
            self.cache['invs'][account.id] = invs
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.cache['trs']:
            # Get form to go to History's tab
            form = self.location(account.url).page.get_historytab_form()
            # Get form to show all transactions
            form = self.location(form.url, data=dict(form)).page.get_historyallpages_form()
            if form:
                self.location(form.url, data=dict(form))
            # Get forms to expand details of all transactions
            for form in self.page.get_historyexpandall_form():
                # Can't async because of ReadTimeout
                self.location(form.url, data=dict(form))
            trs = [t for t in self.page.iter_history()]
            self.cache['trs'][account.id] = trs
        return self.cache['trs'][account.id]

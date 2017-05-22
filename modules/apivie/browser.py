# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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
from weboob.capabilities.base import find_object
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, InvestmentsPage, OperationsPage


__all__ = ['ApivieBrowser']


class ApivieBrowser(LoginBrowser):
    login = URL(r'/$',
                r'/accueil$',
                r'/perte.*',
                LoginPage)
    accounts = URL(r'/accueil-connect', AccountsPage)
    investments = URL(r'/synthese-contrat.*', InvestmentsPage)
    operations = URL(r'/historique-contrat.*', OperationsPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'https://%s' % website
        super(ApivieBrowser, self).__init__(*args, **kwargs)

    def home(self):
        self.location('%s/accueil-connect' % self.BASEURL)

    def do_login(self):
        if not self.login.is_here():
            self.location('/accueil')

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        self.location('/accueil-connect')
        return self.page.iter_accounts()

    @need_login
    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id)

    @need_login
    def iter_investment(self, account):
        self.location('/synthese-contrat', params={'contratId': account.id})

        assert self.investments.is_here()
        return self.page.iter_investment()

    @need_login
    def iter_history(self, account):
        self.location('/historique-contrat', params={'contratId': account.id})

        assert self.operations.is_here()
        return self.page.iter_history()

    @need_login
    def get_subscription_list(self):
        return []

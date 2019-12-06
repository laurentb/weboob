# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded

from .pages import LoginPage, AccountsPage, InvestmentsPage, OperationsPage, InfoPage

__all__ = ['ApivieBrowser']


class ApivieBrowser(LoginBrowser):
    login = URL(r'/$',
                r'/accueil$',
                r'/perte.*',
                LoginPage)
    info = URL(r'/coordonnees.*', InfoPage)
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

        # If the user's contact info is too old the website asks to verify them. We're logged but we can't go further.
        if self.info.is_here():
            error_message = self.page.get_error_message()
            assert error_message, 'Error message location has changed on info page'
            raise ActionNeeded(error_message)

        if self.login.is_here() or self.page is None:
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

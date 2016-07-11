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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, InvestmentsPage, OperationsPage


__all__ = ['ApivieBrowser']


class ApivieBrowser(Browser):
    PROTOCOL = 'https'
    ENCODING = None

    PAGES = {
        'https?://[^/]+/':                      LoginPage,
        'https?://[^/]+/accueil':               LoginPage,
        'https?://[^/]+/perte.*':               LoginPage,
        'https?://[^/]+/accueil-connect':       AccountsPage,
        'https?://[^/]+/synthese-contrat.*':    InvestmentsPage,
        'https?://[^/]+/historique-contrat.*':  OperationsPage,
    }

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://%s/accueil-connect' % self.DOMAIN)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('/accueil', no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def iter_accounts(self):
        self.location('/accueil-connect')
        return self.page.iter_accounts()

    def get_account(self, _id):
        try:
            return next(a for a in self.iter_accounts() if a.id == _id)
        except StopIteration:
            return None

    def iter_investment(self, account):
        self.location(self.buildurl('/synthese-contrat', contratId=account.id))

        assert self.is_on_page(InvestmentsPage)
        return self.page.iter_investment()

    def iter_history(self, account):
        self.location(self.buildurl('/historique-contrat', contratId=account.id))

        assert self.is_on_page(OperationsPage)
        return self.page.iter_history()

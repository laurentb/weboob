# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


import urllib

from weboob.tools.browser import BaseBrowser

from .pages import LoginPage, HomePage, AccountsPage, TransactionsPage


__all__ = ['CarrefourBanque']


class CarrefourBanque(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'services.carrefour-banque.fr'
    ENCODING = 'iso-8859-15'
    PAGES = {'https?://services.carrefour-banque.fr/s2pnet/publ/identification.do':             LoginPage,
             'https?://services.carrefour-banque.fr/stscripts/run.stn/s2p/SommairePS2P':        HomePage,
             'https?://services.carrefour-banque.fr/s2pnet/priv/disponible.do':                 AccountsPage,
             'https?://services.carrefour-banque.fr/s2pnet/priv/consult.do\?btnTelechargement': (TransactionsPage, 'raw'),
            }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if self.is_logged():
            self.location('/s2pnet/priv/disponible.do')
        else:
            self.login()

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.is_logged():
            return

        args = {'login': '',
                'loginCBPASS': self.username.encode(self.ENCODING),
                'motPasse': self.password.encode(self.ENCODING),
                'testJS': 'true',
                'x': 8,
                'y': 4,
               }

        self.location('https://services.carrefour-banque.fr/s2pnet/publ/identification.do', urllib.urlencode(args), no_login=True)

        assert self.is_on_page(LoginPage)

        # raises BrowserIncorrectPassword if no redirect form is found
        self.page.redirect()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('/s2pnet/priv/disponible.do')
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def iter_history(self, account):
        self.location('/s2pnet/priv/consult.do?btnTelechargement')

        assert self.is_on_page(TransactionsPage)
        return self.page.get_history(account)

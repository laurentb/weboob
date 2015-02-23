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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, HomePage, TransactionsPage


__all__ = ['CarrefourBanque']


class CarrefourBanque(LoginBrowser):
    BASEURL = 'https://www.carrefour-banque.fr'

    login = URL('/espace-client/connexion', LoginPage)
    home = URL('/espace-client$', HomePage)
    transactions = URL('/espace-client/(?P<account>.*)/solde-dernieres-operations.*', TransactionsPage)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.login.go()
        self.page.enter_login(self.username)
        self.page.enter_password(self.password)

        if not self.home.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.home.stay_or_go()
        return self.page.get_list()

    @need_login
    def iter_history(self, account):
        self.home.stay_or_go()
        self.location(account._link)

        assert self.transactions.is_here()
        return self.page.get_history(account)

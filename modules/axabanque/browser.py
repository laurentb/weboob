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

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.deprecated.browser.parsers.jsonparser import JsonParser

from .pages import LoginPage, PostLoginPage, AccountsPage, TransactionsPage, CBTransactionsPage, UnavailablePage


__all__ = ['AXABanque']


class AXABanque(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'www.axabanque.fr'
    PAGES = {'https?://www.axa.fr/.sendvirtualkeyboard.json':                               (LoginPage, JsonParser()),
             'https?://www.axa.fr/.loginAxa.json':                                          (PostLoginPage, JsonParser()),
             'https?://www.axabanque.fr/login_errors/indisponibilite.*':                    UnavailablePage,
             'https?://www.axabanque.fr/.*page-indisponible.html.*':                        UnavailablePage,
             'https?://www.axabanque.fr/transactionnel/client/liste-comptes.html':          AccountsPage,
             'https?://www.axabanque.fr/webapp/axabanque/jsp/panorama.faces':               TransactionsPage,
             'https?://www.axabanque.fr/webapp/axabanque/jsp/detailCarteBleu.*.faces':      CBTransactionsPage,
             'https?://www.axabanque.fr/webapp/axabanque/jsp/detail(?!CarteBleu).*.faces':  TransactionsPage,
            }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if self.is_logged():
            self.location('/transactionnel/client/liste-comptes.html')
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

        if not self.is_on_page(LoginPage):
            self.location('https://www.axa.fr/.sendvirtualkeyboard.json', data=urllib.urlencode({'login': self.username}), no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_on_page(PostLoginPage):
            raise BrowserIncorrectPassword()

        if not self.page.redirect():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('/transactionnel/client/liste-comptes.html')

        if self.page.is_password_expired():
            raise BrowserIncorrectPassword()

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if not self.is_on_page(AccountsPage):
            account = self.get_account(account.id)

        if self.page.is_password_expired():
            raise BrowserIncorrectPassword()

        args = account._args
        args['javax.faces.ViewState'] = self.page.get_view_state()
        self.location('/webapp/axabanque/jsp/panorama.faces', urllib.urlencode(args))

        assert self.is_on_page(TransactionsPage)

        self.page.more_history()

        assert self.is_on_page(TransactionsPage)
        return self.page.get_history()

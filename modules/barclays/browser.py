# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from .pages import LoginPage, Login2Page, IndexPage, AccountsPage, TransactionsPage, \
                   CardPage, ValuationPage, LoanPage, MarketPage


__all__ = ['Barclays']


class Barclays(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'www.barclays.fr'
    PAGES = {'https?://.*.barclays.fr/\d-index.html':                       IndexPage,
             'https://.*.barclays.fr/barclaysnetV2/logininstit.do.*':       LoginPage,
             'https://.*.barclays.fr/barclaysnetV2/loginSecurite.do.*':     Login2Page,
             'https://.*.barclays.fr/barclaysnetV2/tbord.do.*':             AccountsPage,
             'https://.*.barclays.fr/barclaysnetV2/releve.do.*':            TransactionsPage,
             'https://.*.barclays.fr/barclaysnetV2/cartes.do.*':            CardPage,
             'https://.*.barclays.fr/barclaysnetV2/valuationViewBank.do.*': ValuationPage,
             'https://.*.barclays.fr/barclaysnetV2/pret.do.*':              LoanPage,
             'https://.*.barclays.fr/barclaysnetV2/titre.do.*':             MarketPage,
            }

    def __init__(self, secret, *args, **kwargs):
        self.secret = secret

        Browser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page is not None and not self.is_on_page((LoginPage, IndexPage, Login2Page))

    def home(self):
        if self.is_logged():
            self.location('tbord.do')
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
            self.location('https://b-net.barclays.fr/barclaysnetV2/logininstit.do?lang=fr&nodoctype=0', no_login=True)

        self.page.login(self.username, self.password)

        if not self.page.has_redirect():
            raise BrowserIncorrectPassword()

        self.location('loginSecurite.do', no_login=True)

        self.page.login(self.secret)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('tbord.do')
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
            self.location('tbord.do')

        self.location(account._link)

        assert self.is_on_page((TransactionsPage, ValuationPage, LoanPage, MarketPage))

        for tr in self.page.get_history():
            yield tr

        for tr in self.get_card_operations(account):
            yield tr

    def get_card_operations(self, account):
        for card in account._card_links:
            if not self.is_on_page(AccountsPage):
                self.location('tbord.do')

            self.location(card)

            assert self.is_on_page(CardPage)

            for tr in self.page.get_history():
                yield tr

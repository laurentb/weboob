# -*- coding: utf-8 -*-

# Copyright(C) 2013  Romain Bignon
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
import re

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser

from .pages import HomePage, LoginPage, LoginErrorPage, AccountsPage, \
                   SavingsPage, TransactionsPage, UselessPage, CardsPage


__all__ = ['Cragr']


class Cragr(Browser):
    PROTOCOL = 'https'
    ENCODING = 'ISO-8859-1'

    PAGES = {'https?://[^/]+/':                                          HomePage,
             'https?://[^/]+/stb/entreeBam':                             LoginPage,
             'https?://[^/]+/stb/entreeBam\?.*typeAuthentification=CLIC_ALLER.*': LoginPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthcomptes':         AccountsPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthepargnes':        SavingsPage,
             'https?://[^/]+/stb/.*act=Releves.*':                       TransactionsPage,
             'https?://[^/]+/stb/collecteNI\?.*sessionAPP=Releves.*':    TransactionsPage,
             'https?://[^/]+/stb/.*/erreur/.*':                          LoginErrorPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Messagesprioritaires': UselessPage,
             'https?://[^/]+/stb/collecteNI\?.*fwkaction=Cartes.*':      CardsPage,
             'https?://[^/]+/stb/collecteNI\?.*fwkaction=Detail.*sessionAPP=Cartes.*': CardsPage,
            }

    class WebsiteNotSupported(Exception):
        pass

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = re.sub('^m\.', 'www.', website)
        self.accounts_url = None
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.login()

    def is_logged(self):
        return self.page is not None and not self.is_on_page(HomePage)

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        # Do we really need to login?
        if self.is_logged():
            self.logger.debug('already logged in')
            return

        if not self.is_on_page(HomePage):
            self.location(self.absurl('/'), no_login=True)

        # On the homepage, we get the URL of the auth service.
        url = self.page.get_post_url()
        if url is None:
            raise self.WebsiteNotSupported()

        # First, post account number to get the password prompt.
        data = {'CCPTE':                self.username.encode(self.ENCODING),
                'canal':                'WEB',
                'hauteur_ecran':        768,
                'largeur_ecran':        1024,
                'liberror':             '',
                'matrice':              'true',
                'origine':              'vitrine',
                'situationTravail':     'BANCAIRE',
                'typeAuthentification': 'CLIC_ALLER',
                'urlOrigine':           self.page.url,
                'vitrine':              0,
               }

        self.location(url, urllib.urlencode(data))

        assert self.is_on_page(LoginPage)

        # Then, post the password.
        self.page.login(self.password)

        # The result of POST is the destination URL.
        url = self.page.get_result_url()

        if not url.startswith('http'):
            raise BrowserIncorrectPassword(url)

        self.location(url)

        if self.is_on_page(LoginErrorPage):
            raise BrowserIncorrectPassword()

        if self.page is None:
            raise self.WebsiteNotSupported()

        if not self.is_on_page(AccountsPage):
            # Sometimes the home page is Releves.
            new_url  = re.sub('act=([^&=]+)', 'act=Synthcomptes', self.page.url, 1)
            self.location(new_url)

        if not self.is_on_page(AccountsPage):
            raise self.WebsiteNotSupported()

        # Store the current url to go back when requesting accounts list.
        self.accounts_url = self.page.url

        # we can deduce the URL to "savings" accounts from the regular accounts one
        self.savings_url  = re.sub('act=([^&=]+)', 'act=Synthepargnes', self.accounts_url, 1)

    def get_accounts_list(self):
        accounts_list = []
        # regular accounts
        if not self.is_on_page(AccountsPage):
            self.location(self.accounts_url)
        accounts_list.extend(self.page.get_list())

        # credit cards
        for cards_page in self.page.cards_pages():
            self.location(cards_page)
            assert self.is_on_page(CardsPage)
            accounts_list.extend(self.page.get_list())

        # savings accounts
        self.location(self.savings_url)
        if self.is_on_page(SavingsPage):
            for account in self.page.get_list():
                if account not in accounts_list:
                    accounts_list.append(account)
        return accounts_list

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == ('%s' % id):
                return a

        return None

    def get_history(self, account):
        # some accounts may exist without a link to any history page
        if account._link is None:
            return

        date_guesser = LinearDateGuesser()
        self.location(account._link)

        if self.is_on_page(CardsPage):
            for tr in self.page.get_history(date_guesser):
                yield tr
        else:
            url = self.page.get_order_by_date_url()

            while url:
                self.location(url)
                assert self.is_on_page(TransactionsPage)

                for tr in self.page.get_history(date_guesser):
                    yield tr

                url = self.page.get_next_url()

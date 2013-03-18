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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser

from .pages import HomePage, LoginPage, LoginErrorPage, AccountsPage, TransactionsPage


__all__ = ['Cragr']


class Cragr(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = 'ISO-8859-1'

    PAGES = {'https?://[^/]+/':                                     HomePage,
             'https?://[^/]+/stb/entreeBam':                        LoginPage,
             'https?://[^/]+/stb/entreeBam\?.*act=Synthcomptes':    AccountsPage,
             'https?://[^/]+/stb/collecteNI\?.*act=Releves.*':      TransactionsPage,
             'https?://[^/]+/stb/collecteNI\?.*sessionAPP=Releves.*': TransactionsPage,
             'https?://[^/]+/stb/.*/erreur/.*':                     LoginErrorPage,
            }

    class WebsiteNotSupported(Exception):
        pass

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = re.sub('^m\.', 'www.', website)
        self.accounts_url = None
        BaseBrowser.__init__(self, *args, **kwargs)

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

        self.location(url)

        if self.is_on_page(LoginErrorPage) or not self.is_logged():
            raise BrowserIncorrectPassword()

        assert self.is_on_page(AccountsPage)

        # Store the current url to go back when requesting accounts list.
        self.accounts_url = self.page.url

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location(self.accounts_url)
        return self.page.get_list()

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

        self.location(account._link)
        url = account._link
        date_guesser = LinearDateGuesser()

        while url:
            self.location(url)
            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history(date_guesser):
                yield tr

            url = self.page.get_next_url()

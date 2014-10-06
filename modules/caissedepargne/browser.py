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


import ssl
import hashlib
from urlparse import urlsplit

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, IndexPage, ErrorPage, UnavailablePage


__all__ = ['CaisseEpargne']


class CaisseEpargne(Browser):
    DOMAIN = 'www.caisse-epargne.fr'
    PROTOCOL = 'https'
    CERTHASH = ['dfff27d6db1fcdf1cea3ab8e3c1ca4f97c971262e95be49f3385b40c97fe640c', '9894ab2088630f341de821a09f1286c525f854f62ac186bd442368b4692c5969']
    PAGES = {'https://[^/]+.caisse-epargne.fr/particuliers/ind_pauthpopup.aspx.*':          LoginPage,
             'https://[^/]+.caisse-epargne.fr/Portail.aspx':                                IndexPage,
             'https://[^/]+.caisse-epargne.fr/login.aspx':                                  ErrorPage,
             'https://[^/]+.caisse-epargne.fr/Pages/logout.aspx.*':                         ErrorPage,
             'https://[^/]+.caisse-epargne.fr/page_hs_dei_.*.aspx':                         UnavailablePage,
            }

    def __init__(self, nuser, *args, **kwargs):
        self.nuser = nuser
        Browser.__init__(self, *args, **kwargs)

    def _certhash(self, domain, port=443):
        # XXX overload the Browser method to force use of TLSv1.
        certs = ssl.get_server_certificate((domain, port), ssl_version=ssl.PROTOCOL_TLSv1)
        return hashlib.sha256(certs).hexdigest()

    def is_logged(self):
        return self.page is not None and not self.is_on_page((LoginPage,ErrorPage))

    def home(self):
        if self.is_logged():
            self.location(self.buildurl('/Portail.aspx'))
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

        self._ua_handlers['_cookies'].cookiejar.clear()
        if not self.is_on_page(LoginPage):
            self.location('https://www.caisse-epargne.fr/particuliers/ind_pauthpopup.aspx?mar=101&reg=&fctpopup=auth&cv=0', no_login=True)

        self.page.login(self.username)
        if not self.page.login2(self.nuser, self.password):
            # perso
            self.page.login3(self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        v = urlsplit(self.page.url)
        self.DOMAIN = v.netloc

    def get_accounts_list(self):
        if self.is_on_page(IndexPage):
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx'))

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def _get_history(self, info):
        if self.is_on_page(IndexPage):
            self.page.go_list()
        else:
            self.location(self.buildurl('/Portail.aspx'))

        self.page.go_history(info)

        while True:
            assert self.is_on_page(IndexPage)

            for tr in self.page.get_history():
                yield tr

            if not self.page.go_next():
                return

    def get_history(self, account):
        return self._get_history(account._info)

    def get_coming(self, account):
        for info in account._card_links:
            for tr in self._get_history(info):
                yield tr

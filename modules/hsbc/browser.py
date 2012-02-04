# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BasePage, BrokenPageError
from .pages.accounts import AccountsListPage, HistoryPage


__all__ = ['HSBC']


class NotLoggedPage(BasePage):
    pass

class HSBC(BaseBrowser):
    DOMAIN = 'client.hsbc.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {'https://client.hsbc.fr/session_absente.html':                 NotLoggedPage,
             'https://client.hsbc.fr/cgi-bin/emcgi\?.*debr=COMPTES_PAN':    AccountsListPage,
             'https://client.hsbc.fr/cgi-bin/emcgi\?.*CPT_IdPrestation=.*': HistoryPage
            }

    _session = None

    def home(self):
        self.login()

    def is_logged(self):
        return self._session is not None and not self.is_on_page(NotLoggedPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        data = {'Ident': self.username}
        r = self.readurl('https://client.hsbc.fr/cgi-bin/emcgi?Appl=WEBACC', urllib.urlencode(data))
        m = re.search('sessionid=([^ "]+)', r, flags=re.MULTILINE)
        if not m:
            raise BrowserIncorrectPassword()

        self._session = m.group(1)

        data = {'Secret': self.password}
        r = self.readurl('https://client.hsbc.fr/cgi-bin/emcgi?sessionid=%s' % self._session, urllib.urlencode(data))
        if r.find('Erreur Identification') >= 0:
            raise BrowserIncorrectPassword()

        m = re.search('url = "/cgi-bin/emcgi\?sessionid=([^& "]+)&debr="', r, flags=re.MULTILINE)
        if not m:
            raise BrokenPageError('Unable to find session token')
        self._session = m.group(1)

    def get_accounts_list(self):
        self.location(self.buildurl('/cgi-bin/emcgi', sessionid=self._session, debr='COMPTES_PAN'))

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsListPage):
            l = self.get_accounts_list()
        else:
            l = self.page.get_list()

        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, link):
        self.location(link)
        return self.page.get_operations()

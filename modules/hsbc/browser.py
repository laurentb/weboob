# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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


from datetime import timedelta
import urllib
import re

from weboob.tools.date import LinearDateGuesser
from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BasePage, BrokenPageError
from weboob.tools.decorators import retry
from .pages.accounts import AccountsListPage, CPTHistoryPage, CardHistoryPage
from .pages.login import LoginPage


__all__ = ['HSBC']


class NotLoggedPage(BasePage):
    pass


class HSBC(BaseBrowser):
    DOMAIN = 'client.hsbc.fr'
    PROTOCOL = 'https'
    CERTHASH = '48d84a782728eeeb622e9ff721688365e24f555ae1aec49b3be33831c7fe24e6'
    ENCODING = None # refer to the HTML encoding
    PAGES = {'https://client.hsbc.fr/session_absente.html':                     NotLoggedPage,
             'https://client.hsbc.fr/cgi-bin/emcgi.*\?.*debr=COMPTES_PAN':      AccountsListPage,
             'https://client.hsbc.fr/cgi-bin/emcgi.*\?.*CPT_IdPrestation=.*':   CPTHistoryPage,
             'https://client.hsbc.fr/cgi-bin/emcgi.*\?.*CB_IdPrestation=.*':    CardHistoryPage,
             'https://www.hsbc.fr/.*':                                          LoginPage,
             'https://client.hsbc.fr/cgi-bin/emcgi':                            LoginPage,
            }

    _session = None

    def __init__(self, username, password, secret, *args, **kwargs):
        self.secret = secret
        BaseBrowser.__init__(self, username, password, *args, **kwargs)

    def home(self):
        self.login()

    def is_logged(self):
        return self._session is not None and not self.is_on_page((NotLoggedPage,LoginPage))

    @retry(BrokenPageError, tries=2)
    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self._ua_handlers['_cookies'].cookiejar.clear()

        if len(self.username) == 11 and self.username.isdigit():
            self.login_france()
        else:
            self.login_world()

    def login_france(self):
        data = {'Ident': self.username}
        r = self.readurl('https://client.hsbc.fr/cgi-bin/emcgi?Appl=WEBACC', urllib.urlencode(data), if_fail='raise')
        m = re.search('sessionid=([^ "]+)', r, flags=re.MULTILINE)
        if not m:
            raise BrowserIncorrectPassword()

        self._session = m.group(1)

        data = {'Secret': self.password}
        r = self.readurl('https://client.hsbc.fr/cgi-bin/emcgi?sessionid=%s' % self._session, urllib.urlencode(data), if_fail='raise')
        if r.find('Erreur Identification') >= 0:
            raise BrowserIncorrectPassword()

        m = re.search('url = "/cgi-bin/emcgi\?sessionid=([^& "]+)&debr="', r, flags=re.MULTILINE)
        if not m:
            raise BrokenPageError('Unable to find session token')

        self._session = m.group(1)

    def login_world(self):
        data = {'Appl':         'WEBACC',
                'CODE_ABONNE':  self.username,
                'Ident':        self.username,
                'ifr':          0,
                'nextPage':     'localsso.hbfr.Redirect',
                'secret':       '',
                'userid':       self.username,
               }
        self.location('https://www.hsbc.fr/1/2/?idv_cmd=idv.Authentication', urllib.urlencode(data), no_login=True)

        self.page.login(self.username, self.secret, self.password)

        error = self.page.get_error()
        if error is not None:
            raise BrowserIncorrectPassword(error)

        self._session = self.page.get_session()

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

    def get_history(self, account):
        if account._link_id is None:
            return

        for tr in self._get_history(account._link_id):
            yield tr

        for card in account._card_links:
            for tr in self._get_history(card):
                yield tr

    def _get_history(self, link):
        num_page = 0
        guesser = LinearDateGuesser(date_max_bump=timedelta(45))
        while link is not None:
            self.location(link)

            if self.page is None:
                return

            for tr in self.page.get_operations(num_page, guesser):
                yield tr

            link = self.page.get_next_link()
            num_page += 1

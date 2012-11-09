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


import urllib

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage


__all__ = ['CreditCooperatif']


class CreditCooperatif(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = 'iso-8859-15'
    PAGES = {'https://[^/]+/banque/sso/ssologin.do".*':                                         LoginPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=mesComptes.*':             AccountsPage
            }

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        self.token = None

        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

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
            self.home()

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

        self.token = self.page.get_token()

    def get_accounts_list(self):
        self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID='mesComptes', token=self.token))
        if self.page.is_error():
            self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID='maSyntheseGratuite', token=self.token))

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(account._params))

        while 1:
            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history():
                yield tr

            next_params = self.page.get_next_params()
            if next_params is None:
                return

            self.location(self.buildurl('/cyber/internet/Page.do', **next_params))

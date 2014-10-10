# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from .pages import LoginPage, LoggedPage, AccountsPage, TransactionsPage, TransactionsJSONPage, ComingTransactionsPage


__all__ = ['CreditCooperatif']


class CreditCooperatif(Browser):
    PROTOCOL = 'https'
    ENCODING = 'iso-8859-15'
    DOMAIN = "www.credit-cooperatif.coop"
    PAGES = {'https://www.credit-cooperatif.coop/portail/particuliers/login.do': LoginPage,
             'https://www.credit-cooperatif.coop/portail/particuliers/authentification.do': LoggedPage,
             'https://www.credit-cooperatif.coop/portail/particuliers/mescomptes/synthese.do': AccountsPage,
             'https://www.credit-cooperatif.coop/portail/particuliers/mescomptes/relevedesoperations.do': TransactionsPage,
             'https://www.credit-cooperatif.coop/portail/particuliers/mescomptes/relevedesoperationsjson.do': (TransactionsJSONPage, 'json'),
             'https://www.credit-cooperatif.coop/portail/particuliers/mescomptes/synthese/operationsencourslien.do': ComingTransactionsPage,
            }

    def home(self):
        self.location("/portail/particuliers/mescomptes/synthese.do")

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

        if self.is_on_page(LoggedPage):
            error = self.page.get_error()
            if error is not None:
                raise BrowserIncorrectPassword(error)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('/portail/particuliers/mescomptes/synthese.do')

        return self.page.get_list()

    def get_history(self, account):
        data = {'accountExternalNumber': account.id}
        self.location('/portail/particuliers/mescomptes/relevedesoperations.do', urllib.urlencode(data))

        data = {'iDisplayLength':  400,
                'iDisplayStart':   0,
                'iSortCol_0':      0,
                'iSortingCols':    1,
                'sColumns':        '',
                'sEcho':           1,
                'sSortDir_0':      'asc',
               }
        self.location('/portail/particuliers/mescomptes/relevedesoperationsjson.do', urllib.urlencode(data))

        return self.page.get_transactions()

    def get_coming(self, account):
        data = {'accountExternalNumber': account.id}
        self.location('/portail/particuliers/mescomptes/synthese/operationsencourslien.do', urllib.urlencode(data))

        assert self.is_on_page(ComingTransactionsPage)

        return self.page.get_transactions()

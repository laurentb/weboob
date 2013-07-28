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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BrokenPageError

from .pages import LoginPage, IndexPage, AccountsPage, TransactionsPage, UnavailablePage, RedirectPage, HomePage


__all__ = ['BanquePopulaire']


class BanquePopulaire(BaseBrowser):
    PROTOCOL = 'https'
    ENCODING = 'iso-8859-15'
    PAGES = {'https://[^/]+/auth/UI/Login.*':                                                   LoginPage,
             'https://[^/]+/cyber/internet/Login.do':                                           IndexPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=mesComptes.*':             AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=maSyntheseGratuite.*':     AccountsPage,
             'https://[^/]+/cyber/internet/StartTask.do\?taskInfoOID=accueilSynthese.*':        AccountsPage,
             'https://[^/]+/cyber/internet/ContinueTask.do\?.*dialogActionPerformed=SOLDE.*':   TransactionsPage,
             'https://[^/]+/cyber/internet/Page.do\?.*':                                        TransactionsPage,
             'https://[^/]+/cyber/internet/Sort.do\?.*':                                        TransactionsPage,
             'https://[^/]+/s3f-web/indispo.*':                                                 UnavailablePage,
             'https://[^/]+/portailinternet/_layouts/Ibp.Cyi.Layouts/RedirectSegment.aspx.*':   RedirectPage,
             'https://[^/]+/portailinternet/Catalogue/Segments/.*.aspx\?vary=(?P<vary>.*)':     HomePage,
             'https://[^/]+/portailinternet/Pages/.*.aspx\?vary=(?P<vary>.*)':                  HomePage,
             'https://[^/]+/portailinternet/Pages/default.aspx':                                HomePage,
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
            self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID='mesComptesPRO', token=self.token))
        if self.page.is_error():
            self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID='maSyntheseGratuite', token=self.token))
        if self.page.is_error():
            self.location(self.buildurl('/cyber/internet/StartTask.do', taskInfoOID='accueilSynthese', token=self.token))
        if self.page.is_error():
            raise BrokenPageError('Unable to go on the accounts list page')

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
        self.location('/cyber/internet/ContinueTask.do', urllib.urlencode(account._params))

        # Sort by values dates (see comment in TransactionsPage.get_history)
        self.select_form(predicate=lambda form: form.attrs.get('id', '') == 'myForm')
        self.form.action = self.absurl('/cyber/internet/Sort.do?property=tbl1&sortBlocId=blc2&columnName=dateValeur')
        self.submit()

        while True:
            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history():
                yield tr

            next_params = self.page.get_next_params()
            if next_params is None:
                return

            self.location(self.buildurl('/cyber/internet/Page.do', **next_params))

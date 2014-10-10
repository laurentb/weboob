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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, CreditLoggedPage, AccountsPage, TransactionsPage, TransactionsJSONPage, ComingTransactionsPage


__all__ = ['CreditCooperatif']


class CreditCooperatif(LoginBrowser):
    BASEURL = "https://www.credit-cooperatif.coop"

    loginpage = URL('/portail//particuliers/login.do', LoginPage)
    loggedpage = URL('/portail/particuliers/authentification.do', CreditLoggedPage)
    accountspage = URL('/portail/particuliers/mescomptes/synthese.do', AccountsPage)
    transactionpage = URL('/portail/particuliers/mescomptes/relevedesoperations.do', TransactionsPage)
    transactjsonpage = URL('/portail/particuliers/mescomptes/relevedesoperationsjson.do', TransactionsJSONPage)
    comingpage = URL('/portail/particuliers/mescomptes/synthese/operationsencourslien.do', ComingTransactionsPage)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.loginpage.stay_or_go()
        self.page.login(self.username, self.password)

        if self.loggedpage.is_here():
            error = self.page.get_error()
            if error is None:
                return

        raise BrowserIncorrectPassword(error)

    @need_login
    def get_accounts_list(self):
        self.accountspage.stay_or_go()

        return self.page.get_list()

    @need_login
    def get_history(self, account):
        data = {'accountExternalNumber': account.id}
        self.transactionpage.go(data=data)

        data = {'iDisplayLength':  400,
                'iDisplayStart':   0,
                'iSortCol_0':      0,
                'iSortingCols':    1,
                'sColumns':        '',
                'sEcho':           1,
                'sSortDir_0':      'asc',
                }
        self.transactjsonpage.go(data=data)

        return self.page.get_transactions()

    @need_login
    def get_coming(self, account):
        data = {'accountExternalNumber': account.id}
        self.comingpage.go(data=data)

        assert self.comingpage.is_here()

        return self.page.get_transactions()

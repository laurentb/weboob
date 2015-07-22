# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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

from .pages import LoginPage, AccountsPage, HistoryPage


__all__ = ['BNPCompany']


class BNPCompany(LoginBrowser):
    BASEURL = 'https://secure1.entreprises.bnpparibas.net'

    login = URL('/sommaire/jsp/identification.jsp', LoginPage)
    accounts = URL('/NCCPresentationWeb/e10_soldes/liste_soldes.do', AccountsPage)
    history = URL('/NCCPresentationWeb/m04_selectionCompteGroupe/init.do?type=compte&identifiant=', HistoryPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()
        self.login.go()
        self.login.go()
        assert self.login.is_here()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def get_account(self, _id):
        pass

    @need_login
    def iter_history(self, account):
        pass

    @need_login
    def iter_coming_operations(self, account):
        pass

    def iter_investment(self, account):
        raise NotImplementedError()

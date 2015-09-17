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


from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, ErrorPage, AccountsPage, HistoryPage, LoanHistoryPage


class BforbankBrowser(LoginBrowser):
    BASEURL = 'https://www.bforbank.com'

    login = URL('/connexion-client/service/login\?urlBack=%2Fespace-client', LoginPage)
    error = URL('/connexion-client/service/auth', ErrorPage)
    home = URL('/espace-client/$', AccountsPage)
    loan_history = URL('/espace-client/livret/consultation.*', LoanHistoryPage)
    history = URL('/espace-client/consultation/operations/.*', HistoryPage)

    def __init__(self, birthdate, *args, **kwargs):
        super(BforbankBrowser, self).__init__(*args, **kwargs)
        self.birthdate = birthdate

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()
        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.birthdate, self.username, self.password)
        if self.error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        self.home.stay_or_go()
        return self.page.iter_accounts()

    @need_login
    def get_history(self, account):
        self.location(account._link.replace('tableauDeBord', 'operations'))
        return self.page.get_operations()

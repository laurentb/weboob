# -*- coding: utf-8 -*-

# Copyright(C) 2015 Vincent Paredes
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

from .pages import LoginPage, AccountsPage, TransactionsPage, PassModificationPage


class SogecartesBrowser(LoginBrowser):
    BASEURL = 'https://www.sogecartenet.fr/'

    login = URL('/internationalisation/identification', LoginPage)
    pass_modification = URL('/internationalisation/./modificationMotPasse.*', PassModificationPage)
    accounts = URL('/internationalisation/gestionParcCartes', AccountsPage)
    transactions = URL('/internationalisation/csv/operationsParCarte.*', TransactionsPage)

    def load_state(self, state):
        pass

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        data = {"USER": self.username,
                "PWD": self.password,
                "ACCES": "PE",
                "LANGUE": "en",
                "QUEFAIRE": "LOGIN",
                }
        self.login.go(data=data)

    @need_login
    def iter_accounts(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def get_history(self, account):
        if not account._url:
            return ([])
        self.location(account._url)
        assert self.transactions.is_here()
        return self.page.get_history()

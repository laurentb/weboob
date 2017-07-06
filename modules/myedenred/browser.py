# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from .pages import LoginPage, AccountsPage, TransactionsPage


class MyedenredBrowser(LoginBrowser):
    BASEURL = 'https://www.myedenred.fr'

    login = URL(r'/ctr\?Length=7',
                r'/ExtendedAccount/Logon', LoginPage)
    accounts = URL(r'/$', AccountsPage)
    transactions = URL('/Card/TransactionSet', TransactionsPage)

    def __init__(self, *args, **kwargs):
        super(MyedenredBrowser, self).__init__(*args, **kwargs)

        self.docs = {}

    def do_login(self):
        self.login.go(data={'Email': self.username, 'Password': self.password, 'RememberMe': 'false',
                            'X-Requested-With': 'XMLHttpRequest', 'ReturnUrl': '/'})
        self.accounts.go()
        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_accounts_list(self):
        return self.accounts.stay_or_go().iter_accounts()

    @need_login
    def iter_history(self, account):
        history = self.transactions.go(data={'command': 'Charger les 10 transactions suivantes',
                                            'ErfBenId': account._product_token,
                                            'ProductCode': account._product_type,
                                            'SortBy': 'DateOperation',
                                            'StartDate': '',
                                            'EndDate': '',
                                            'PageNum': 10,
                                            'OperationType': 'Debit',
                                            'failed': 'false',
                                            'X-Requested-With': 'XMLHttpRequest'
                                            })
        if account.id not in self.docs:
            self.docs[account.id] = [d for d in history.iter_transactions(subid=account.id)]
        return self.docs[account.id]

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from datetime import timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.date import LinearDateGuesser

from .pages import LoginPage, AccountsPage, AccountDetailsPage, TransactionsPage

class MyedenredBrowser(LoginBrowser):
    BASEURL = 'https://www.myedenred.fr'

    login = URL(r'/ctr\?Length=7',
                r'/ExtendedAccount/Logon', LoginPage)
    accounts = URL(r'/$', AccountsPage)
    accounts_details = URL(r'/ExtendedHome/ProductLine\?benId=(?P<token>\d+)', AccountDetailsPage)
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
    def iter_accounts(self):
        for acc_id in self.accounts.stay_or_go().get_accounts_id():
            yield self.accounts_details.go(headers={'X-Requested-With': 'XMLHttpRequest'},
                                                 token=acc_id).get_account()


    @need_login
    def iter_history(self, account):
        self.transactions.go(data={
            'command': 'Charger les 10 transactions suivantes',
            'ErfBenId': account._product_token,
            'ProductCode': account._product_type,
            'SortBy': 'DateOperation',
            'StartDate': '',
            'EndDate': '',
            'PageNum': 10,
            'OperationType': 'Default',
            'failed': 'false',
            'X-Requested-With': 'XMLHttpRequest'
        })
        for tr in self.page.iter_transactions(subid=account.id, date_guesser=LinearDateGuesser(date_max_bump=timedelta(45))):
            yield tr

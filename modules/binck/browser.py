# -*- coding: utf-8 -*-

# Copyright(C) 2018 Arthur Huillet
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

from .pages import LoginPage, AccountsList, TransactionHistoryJSON, AccountSelectionBar, InvestmentListJSON

__all__ = ['Binck']


class Binck(LoginBrowser):
    BASEURL = 'https://web.binck.fr/'

    # login and account overview are easy. Other pages are stateful and use the
    # current account that is sent via a POST request that includes a one-time
    # verification token
    login_page = URL('/logon$', LoginPage)
    accounts_page = URL('/AccountsOverview/Index', AccountsList)
    transaction_history_json = URL('/TransactionsOverview/GetTransactions', TransactionHistoryJSON)
    investment_list_json = URL('/PortfolioOverview/GetPortfolioOverview', InvestmentListJSON)
    account_history_page = URL('/TransactionsOverview/FilteredOverview', AccountSelectionBar)
    investment_page = URL('/PortfolioOverview/Index', AccountSelectionBar)
    generic_page_with_account_selector = URL('/Home/Index', AccountSelectionBar)

    def __init__(self, *args, **kwargs):
        super(Binck, self).__init__(*args, **kwargs)
        self.current_account = None
        self.verification_token = None

    def do_login(self):
        self.login_page.stay_or_go()
        self.page.login(self.username, self.password)

        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.accounts_page.stay_or_go()
        return self.page.get_list()

    def make_account_current(self, account):
        self.token = self.page.get_account_selector_verification_token()
        self.location('/Header/SwitchAccount', data={'__RequestVerificationToken': self.token, 'accountNumber': account.id})
        self.token = self.page.get_account_selector_verification_token()
        self.current_account = account

    @need_login
    def iter_investment(self, account):
        self.investment_page.stay_or_go()
        self.make_account_current(account)
        self.location('/PortfolioOverview/GetPortfolioOverview', data={'grouping': 'SecurityCategory'},
                      headers={'__RequestVerificationToken': self.token})
        return self.page.iter_investment()

    @need_login
    def iter_history(self, account):
        # Not very useful as Binck's history page sucks (descriptions make no sense)
        self.account_history_page.stay_or_go()
        self.make_account_current(account)
        # XXX handle other currencies than EUR
        self.location('/TransactionsOverview/GetTransactions',
                      data={'currencyCode': 'EUR', 'mutationGroup': '', 'startDate': '', 'endDate': '', 'isFilteredOverview': True},
                      headers={'__RequestVerificationToken': self.token})

        return self.page.iter_history()

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
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

import datetime

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.json import json

from dateutil.relativedelta import relativedelta

from .pages import LoginPage, AccountsPage, InvestmentPage, HistoryPage


class DegiroBrowser(LoginBrowser):
    BASEURL = 'https://trader.degiro.nl'

    login = URL('/login/secure/login', LoginPage)
    client = URL('/pa/secure/client\?sessionId=(?P<sessionId>.*)', LoginPage)
    product = URL(r'/product_search/secure/v5/products/info\?sessionId=(?P<sessionId>.*)', InvestmentPage)
    accounts = URL('/trading(?P<staging>\w*)/secure/v5/update/(?P<accountId>.*);jsessionid=(?P<sessionId>.*)\?historicalOrders=0' +
                   '&orders=0&portfolio=0&totalPortfolio=0&transactions=0&alerts=0&cashFunds=0&currencyExchange=0&',
                   AccountsPage)
    transaction_investments = URL('/reporting/secure/v4/transactions\?fromDate=(?P<fromDate>.*)' +
                                  '&groupTransactionsByOrder=false&intAccount=(?P<accountId>.*)' +
                                  '&orderId=&product=&sessionId=(?P<sessionId>.*)' +
                                  '&toDate=(?P<toDate>.*)',
                                  HistoryPage)
    history = URL('/reporting/secure/v4/accountoverview\?fromDate=(?P<fromDate>.*)' +
                  '&groupTransactionsByOrder=false&intAccount=(?P<accountId>.*)' +
                  '&orderId=&product=&sessionId=(?P<sessionId>.*)&toDate=(?P<toDate>.*)',
                   HistoryPage)

    def __init__(self, *args, **kwargs):
        super(DegiroBrowser, self).__init__(*args, **kwargs)

        self.intAccount = None
        self.name = None
        self.sessionId = None
        self.account = None
        self.invs = {}
        self.trs = {}
        self.products = {}

    def do_login(self):
        try:
            self.login.go(data=json.dumps({'username': self.username, 'password': self.password}))
        except ClientError as e:
            if e.response.status_code == 400:
                raise BrowserIncorrectPassword()
            raise

        self.sessionId = self.page.get_session_id()

        self.client.go(sessionId=self.sessionId)

        self.intAccount = self.page.get_information('intAccount')
        self.name = self.page.get_information('displayName')

    @need_login
    def iter_accounts(self):
        if self.account is None:
            staging = '_s' if 'staging' in self.sessionId else ''
            self.accounts.stay_or_go(staging=staging, accountId=self.intAccount, sessionId=self.sessionId)
            self.account = self.page.get_account()
        yield self.account

    @need_login
    def iter_investment(self, account):
        if account.id not in self.invs:
            staging = '_s' if 'staging' in self.sessionId else ''
            self.accounts.stay_or_go(staging=staging, accountId=self.intAccount, sessionId=self.sessionId)
            self.invs[account.id] = list(self.page.iter_investment())
            # Retrieve liquidities on another page, they aren't available in the account page
            dateFmt = "%d/%m/%Y"
            toDate = datetime.datetime.now()
            fromDate = toDate - relativedelta(years=1)
            self.history.go(fromDate=fromDate.strftime(dateFmt), toDate=toDate.strftime(dateFmt), accountId=self.intAccount, sessionId=self.sessionId)
            if self.history.is_here():
                self.invs[account.id].append(self.page.get_liquidities())
        return self.invs[account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.trs:
            dateFmt = "%d/%m/%Y"
            toDate = datetime.datetime.now()
            fromDate = toDate - relativedelta(years=1)

            self.transaction_investments.go(fromDate=fromDate.strftime(dateFmt), toDate=toDate.strftime(dateFmt),
                                            accountId=self.intAccount, sessionId=self.sessionId)

            self.fetch_products(list(self.page.get_products()))

            transaction_investments = list(self.page.iter_transaction_investments())
            self.history.go(fromDate=fromDate.strftime(dateFmt), toDate=toDate.strftime(dateFmt),
                            accountId=self.intAccount, sessionId=self.sessionId)

            # the list can be pretty big, and the tr list too
            # avoid doing O(n*n) operation
            trinv_dict = {(inv.code, inv._action, inv._datetime): inv for inv in transaction_investments}

            trs = list(self.page.iter_history(transaction_investments=NoCopy(trinv_dict)))
            self.trs[account.id] = trs
        return self.trs[account.id]

    def fetch_products(self, ids):
        ids = list(set(ids) - set(self.products.keys()))
        page = self.product.open(data=json.dumps(ids),
                                 sessionId=self.sessionId,
                                 headers={'Content-Type': 'application/json;charset=UTF-8'})
        self.products.update(page.get_products())

    def get_product(self, id):
        if id not in self.products:
            self.fetch_products([id])
        return self.products[id]


class NoCopy(object):
    # params passed to a @method are deepcopied, in each iteration of ItemElement
    # so we want to avoid repeatedly copying objects since we don't intend to modify them

    def __init__(self, v):
        self.v = v

    def __deepcopy__(self, memo):
        return self

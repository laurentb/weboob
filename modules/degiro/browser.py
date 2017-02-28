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
    product = URL('/product_search/secure/v4/product/info\?intAccount=(?P<accountId>.*)&sessionId=(?P<sessionId>.*)', InvestmentPage)
    accounts = URL('/trading/secure/v5/update/(?P<accountId>.*);jsessionid=(?P<sessionId>.*)\?historicalOrders=0' + \
                   '&orders=0' + \
                   '&portfolio=0' + \
                   '&totalPortfolio=0' + \
                   '&transactions=0' + \
                   '&alerts=0' + \
                   '&cashFunds=0' + \
                   '&currencyExchange=0&', AccountsPage)
    transaction_investments = URL('/reporting/secure/v4/transactions\?fromDate=(?P<fromDate>.*)' + \
                                  '&groupTransactionsByOrder=false' + \
                                  '&intAccount=(?P<accountId>.*)' + \
                                  '&orderId=' + \
                                  '&product=' + \
                                  '&sessionId=(?P<sessionId>.*)' + \
                                  '&toDate=(?P<toDate>.*)', HistoryPage)
    history = URL('/reporting/secure/v4/accountoverview\?fromDate=(?P<fromDate>.*)' + \
                  '&groupTransactionsByOrder=false' + \
                  '&intAccount=(?P<accountId>.*)' + \
                  '&orderId=' + \
                  '&product=' + \
                  '&sessionId=(?P<sessionId>.*)' + \
                  '&toDate=(?P<toDate>.*)', HistoryPage)

    def __init__(self, *args, **kwargs):
        super(DegiroBrowser, self).__init__(*args, **kwargs)

        self.cache = {
            'invs': {},
            'trs': {},
            'sessionId': None,
            'client': {
                'intAccount': None,
                'name': None
            }
        }

    def do_login(self):
        try:
            self.login.go(data=json.dumps({'username': self.username, 'password': self.password}))
        except ClientError as e:
            if e.response.status_code == 400:
                raise BrowserIncorrectPassword()
            raise

        self.cache['sessionId'] = self.page.get_session_id()

        self.client.go(sessionId=self.cache['sessionId'])

        self.cache['client']['intAccount'] = self.page.get_information('intAccount')
        self.cache['client']['name'] = self.page.get_information('displayName')

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            self.cache['accs'] = self.accounts.stay_or_go(accountId=self.cache['client']['intAccount'], sessionId=self.cache['sessionId']).iter_accounts()
        yield self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            self.cache['invs'][account.id] = [i for i in self.accounts.stay_or_go(accountId=self.cache['client']['intAccount'], sessionId=self.cache['sessionId']).iter_investment()]
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.cache['trs']:
            dateFmt = "%d/%m/%Y"
            toDate = datetime.datetime.now()
            fromDate = toDate - relativedelta(years=1)

            transaction_investments = [t for t in self.transaction_investments.go(fromDate=fromDate.strftime(dateFmt), \
                                                                  accountId=self.cache['client']['intAccount'], \
                                                                  sessionId=self.cache['sessionId'], \
                                                                  toDate=toDate.strftime(dateFmt)).iter_transaction_investments()]

            trs = [t for t in self.history.go(fromDate=fromDate.strftime(dateFmt), \
                                             accountId=self.cache['client']['intAccount'], \
                                             sessionId=self.cache['sessionId'], \
                                             toDate=toDate.strftime(dateFmt)).iter_history(transaction_investments=transaction_investments)]

            self.cache['trs'][account.id] = trs
        return self.cache['trs'][account.id]

    @need_login
    def search_product(self, productId):
        return self.product.go(data=json.dumps([productId]), \
                               accountId=self.cache['client']['intAccount'], \
                               sessionId=self.cache['sessionId'], \
                               headers={'Content-Type': 'application/json;charset=UTF-8'})

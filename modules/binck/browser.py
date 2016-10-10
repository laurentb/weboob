# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from .pages import LoginPage, AccountsPage, InvestmentPage, HistoryPage


class BinckBrowser(LoginBrowser):
    BASEURL = 'https://web.binck.fr'

    login = URL('/Logon', LoginPage)
    accounts = URL('/AccountsOverview', '/$', AccountsPage)
    investment = URL('/PortfolioOverview/GetPortfolioOverview', InvestmentPage)
    history = URL('/TransactionsOverview/GetTransactions',
                  '/TransactionsOverview/FilteredOverview', HistoryPage)

    def __init__(self, *args, **kwargs):
        super(BinckBrowser, self).__init__(*args, **kwargs)
        self.cache = {}
        self.cache['invs'] = {}
        self.cache['trs'] = {}

    def deinit(self):
        if self.page.logged:
            self.location("/Account/Logoff")
        super(BinckBrowser, self).deinit()

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def iter_accounts(self):
        if 'accs' not in self.cache.keys():
            accs = []
            for a in self.accounts.go().iter_accounts():
                self.accounts.stay_or_go().go_toaccount(a.id)
                a.iban = self.page.get_iban()
                # Get token
                token = self.page.get_token()
                # Get investment page
                data = {'grouping': "SecurityCategory"}
                a._invpage = self.investment.go(data=data, headers=token) \
                    if self.page.is_investment() else None
                if a._invpage:
                    a.valuation_diff = a._invpage.get_valuation_diff()
                # Get history page
                data = [('currencyCode', a.currency), ('startDate', ""), ('endDate', "")]
                a._histpages = [self.history.go(data=data, headers=token)]
                while self.page.doc['EndOfData'] is False:
                    a._histpages.append(self.history.go(data=self.page.get_nextpage_data(data[:]), headers=token))
                accs.append(a)
            self.cache['accs'] = accs
        return self.cache['accs']

    @need_login
    def iter_investment(self, account):
        if account.id not in self.cache['invs']:
            invs = [i for i in account._invpage.iter_investment()] \
                if account._invpage else []
            self.cache['invs'][account.id] = invs
        return self.cache['invs'][account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.cache['trs']:
            trs = []
            for page in account._histpages:
                trs.extend([t for t in page.iter_history()])
            self.cache['trs'][account.id] = trs
        return self.cache['trs'][account.id]

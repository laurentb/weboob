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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.browser.exceptions import HTTPNotFound
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages import (
    LoginPage, AccountsPage, HomePage, InvestmentPage, HistoryPage,
    QuestionPage, ChangePassPage, LogonFlowPage, ViewPage, SwitchPage,
)


class BinckBrowser(LoginBrowser):
    BASEURL = 'https://web.binck.fr'

    login = URL(r'/Logon', LoginPage)
    view = URL('PersonIntroduction/Index', ViewPage)
    logon_flow = URL(r'/AmlQuestionnairesOverview/LogonFlow$', LogonFlowPage)

    accounts = URL(r'/PersonAccountOverview/Index', AccountsPage)
    account_switch = URL('/Header/SwitchAccount', SwitchPage)
    home_page = URL('/Home/Index', HomePage)

    investment = URL(r'/PortfolioOverview/GetPortfolioOverview', InvestmentPage)
    history = URL(r'/TransactionsOverview/GetTransactions',
                  r'/TransactionsOverview/FilteredOverview', HistoryPage)
    questions = URL(r'/FDL_Complex_FR_Compte', QuestionPage)
    change_pass = URL(r'/ChangePassword/Index', ChangePassPage)

    def deinit(self):
        if self.page and self.page.logged:
            self.location("/Account/Logoff")
        super(BinckBrowser, self).deinit()

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            error = self.page.get_error()
            if error and 'mot de passe' in error:
                raise BrowserIncorrectPassword(error)
            elif error and any((
                'Votre compte a été bloqué / clôturé' in error,
                'Votre compte est bloqué, veuillez contacter le Service Clients' in error,
            )):
                raise ActionNeeded(error)
            raise AssertionError('Unhandled behavior at login: error is "{}"'.format(error))
        elif self.view.is_here():
            self.location(self.page.skip_tuto())

    @need_login
    def iter_accounts(self):
        self.accounts.go()
        for a in self.page.iter_accounts():
            self.accounts.stay_or_go()
            token = self.page.get_token()
            data = {'accountNumber': a.id}
            # Important: the "switch" request without the token will lead to a 500 error
            self.account_switch.go(data=data, headers=token)

            # We must get the new token almost everytime we get a new page:
            token = self.page.get_token()
            try:
                data = {'grouping': 'SecurityCategory'}
                a._invpage = self.investment.go(data=data, headers=token)
            except HTTPNotFound:
                # if it is not an invest account, the portfolio link may be present but hidden and return a 404
                a._invpage = None

            if a._invpage:
                a.valuation_diff = a._invpage.get_valuation_diff()

            # Get history page
            data = [('currencyCode', a.currency), ('startDate', ""), ('endDate', "")]
            a._histpages = [self.history.go(data=data, headers=token)]
            while self.page.doc['EndOfData'] is False:
                a._histpages.append(self.history.go(data=self.page.get_nextpage_data(data[:]), headers=token))

            yield a

    @need_login
    def iter_investment(self, account):
        # Add liquidity investment
        if account._liquidity:
            yield create_french_liquidity(account._liquidity)
        if account._invpage:
            for inv in account._invpage.iter_investment(currency=account.currency):
                yield inv

    @need_login
    def iter_history(self, account):
        for page in account._histpages:
            for tr in page.iter_history():
                yield tr

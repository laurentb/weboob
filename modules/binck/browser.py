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


from lxml import etree
from io import StringIO

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.capabilities.bank import Investment

from .pages import LoginPage, AccountsPage, InvestmentPage, HistoryPage, QuestionPage,\
                   ChangePassPage, LogonFlowPage


class BinckBrowser(LoginBrowser):
    BASEURL = 'https://web.binck.fr'

    login = URL('/Logon', LoginPage)
    logon_flow = URL('/AmlQuestionnairesOverview/LogonFlow$', LogonFlowPage)
    accounts = URL('/AccountsOverview',
                   '/$',
                   '/Home/Index',
                   AccountsPage)
    investment = URL('/PortfolioOverview/GetPortfolioOverview', InvestmentPage)
    history = URL('/TransactionsOverview/GetTransactions',
                  '/TransactionsOverview/FilteredOverview', HistoryPage)
    questions = URL('/FDL_Complex_FR_Compte', QuestionPage)
    change_pass = URL('/EditSetting/GetSetting\?code=MutationPassword', ChangePassPage)

    def deinit(self):
        if self.page and self.page.logged:
            self.location("/Account/Logoff")
        super(BinckBrowser, self).deinit()

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def iter_accounts(self):
        for a in self.accounts.go().iter_accounts():
            try:
                self.accounts.stay_or_go().go_toaccount(a.id)
            except ServerError as exception:
                # get html error to parse
                parser = etree.HTMLParser()
                html_error = etree.parse(StringIO(exception.response.text), parser)
                account_error = html_error.xpath('//p[contains(text(), "Votre compte est")]/text()')
                if account_error:
                    raise ActionNeeded(account_error[0])
                else:
                    raise

            a.iban = self.page.get_iban()
            # Get token
            token = self.page.get_token()
            # Get investment page
            data = {'grouping': "SecurityCategory"}
            try:
                a._invpage = self.investment.go(data=data, headers=token) \
                    if self.page.is_investment() else None
            except HTTPNotFound:
                # if it's not an invest account, the portfolio link may be present but hidden and return a 404
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
        if account._invpage:
            for inv in account._invpage.iter_investment():
                yield inv
            # Add liquidity investment
            if account.liquidity:
                inv = Investment()
                inv.code = u"XX-liquidity"
                inv.label = u"Liquidités"
                inv.valuation = account.liquidity
                yield inv

    @need_login
    def iter_history(self, account):
        for page in account._histpages:
            for tr in page.iter_history():
                yield tr

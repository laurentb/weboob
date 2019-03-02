# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from lxml import etree
from io import StringIO

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages import (
    LoginPage, HomePage, AccountsPage, OldAccountsPage, HistoryPage, InvestmentPage, InvestDetailPage,
    InvestmentListPage, QuestionPage, ChangePassPage, LogonFlowPage, ViewPage, SwitchPage,
)


class BinckBrowser(LoginBrowser):
    BASEURL = 'https://web.binck.fr'

    ''' Delete this attribute when old website is obsolete '''
    old_website_connection = False

    login = URL(r'/Logon', LoginPage)
    view = URL('/PersonIntroduction/Index', ViewPage)
    logon_flow = URL(r'/AmlQuestionnairesOverview/LogonFlow$', LogonFlowPage)

    accounts = URL(r'/PersonAccountOverview/Index', AccountsPage)
    old_accounts = URL(r'/AccountsOverview/Index', OldAccountsPage)

    account_switch = URL('/Header/SwitchAccount', SwitchPage)
    home_page = URL(r'/$',
                    r'/Home/Index', HomePage)

    investment = URL(r'/PortfolioOverview/GetPortfolioOverview', InvestmentPage)
    investment_list = URL(r'PortfolioOverview$', InvestmentListPage)
    invest_detail = URL(r'/SecurityInformation/Get', InvestDetailPage)

    history = URL(r'/TransactionsOverview/GetTransactions',
                  r'/TransactionsOverview/FilteredOverview', HistoryPage)
    questions = URL(r'/FDL_Complex_FR_Compte',
                    r'FsmaMandatoryQuestionnairesOverview', QuestionPage)
    change_pass = URL(r'/ChangePassword/Index',
                      r'/EditSetting/GetSetting\?code=MutationPassword', ChangePassPage)

    def deinit(self):
        if self.page and self.page.logged:
            self.location('/Account/Logoff')
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

    @need_login
    def switch_account(self, account_id):
        self.accounts.stay_or_go()
        if self.accounts.is_here():
            token = self.page.get_token()
        data = {'accountNumber': account_id}
        # Important: the "switch" request without the token will return a 500 error
        self.account_switch.go(data=data, headers=token)
        # We should be automatically redirected to the accounts page:
        assert self.accounts.is_here(), 'switch_account did not redirect to AccountsPage properly'

    @need_login
    def iter_accounts(self):
        self.accounts.stay_or_go()
        if self.page.has_accounts_table():
            for a in self.page.iter_accounts():
                ''' Delete these attributes when old website is obsolete '''
                a._invpage = None
                a._histpages = None

                self.switch_account(a.id)
                # We must get the new token almost everytime we get a new page:
                if self.accounts.is_here():
                    token = self.page.get_token()
                # Get valuation_diff from the investment page
                try:
                    data = {'grouping': 'SecurityCategory'}
                    a.valuation_diff = self.investment.go(data=data, headers=token).get_valuation_diff()
                except HTTPNotFound:
                    # if it is not an invest account, the portfolio link may be present but hidden and return a 404
                    a.valuation_diff = None
                yield a

        # Some Binck connections don't have any accounts on the new AccountsPage,
        # so we need to fetch them on the OldAccountsPage for now:
        else:
            ''' Delete this part when old website is obsolete '''
            self.old_website_connection = True
            self.old_accounts.go()
            for a in self.page.iter_accounts():
                try:
                    self.old_accounts.stay_or_go().go_to_account(a.id)
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
        # Start with liquidities:
        if account._liquidity:
            yield create_french_liquidity(account._liquidity)

        ''' Delete this part when old website is obsolete '''
        if self.old_website_connection:
            self.old_accounts.stay_or_go().go_to_account(account.id)
            if account._invpage:
                for inv in account._invpage.iter_investment(currency=account.currency):
                    if not inv.code:
                        params = {'securityId': inv._security_id}
                        self.invest_detail.go(params=params)
                        if self.invest_detail.is_here():
                            inv.code, inv.code_type = self.page.get_isin_code_and_type()
                    yield inv
            return

        self.switch_account(account.id)
        token = self.page.get_token()

        try:
            data = {'grouping': 'SecurityCategory'}
            self.investment.go(data=data, headers=token)
        except HTTPNotFound:
            return

        for inv in self.page.iter_investment(currency=account.currency):
            yield inv

    @need_login
    def iter_history(self, account):
        ''' Delete this part when old website is obsolete '''
        if self.old_website_connection:
            if account._histpages:
                for page in account._histpages:
                    for tr in page.iter_history():
                        yield tr
            return

        self.switch_account(account.id)
        token = self.page.get_token()
        data = [('currencyCode', account.currency), ('startDate', ''), ('endDate', '')]
        history_pages = [self.history.go(data=data, headers=token)]
        while self.page.doc['EndOfData'] is False:
            history_pages.append(self.history.go(data=self.page.get_nextpage_data(data[:]), headers=token))

        for page in history_pages:
            for tr in page.iter_history():
                yield tr

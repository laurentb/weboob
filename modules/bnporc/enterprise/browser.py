# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from datetime import datetime

from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta

from weboob.browser import LoginBrowser, need_login
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import Account
from weboob.exceptions import BrowserIncorrectPassword, BrowserForbidden
from weboob.browser.url import URL
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    LoginPage, AuthPage, AccountsPage, AccountHistoryViewPage, AccountHistoryPage,
    ActionNeededPage, TransactionPage, MarketPage, InvestPage,
)


__all__ = ['BNPEnterprise']


class BNPEnterprise(LoginBrowser):
    BASEURL = 'https://secure1.entreprises.bnpparibas.net'

    login = URL('/sommaire/jsp/identification.jsp',
                '/sommaire/generateImg', LoginPage)
    auth = URL('/sommaire/PseMenuServlet', AuthPage)
    accounts = URL('/NCCPresentationWeb/e10_soldes/liste_soldes.do', AccountsPage)
    account_history_view = URL('/NCCPresentationWeb/e10_soldes/init.do\?nccIdSelected=NCC_Soldes',
                               '/NCCPresentationWeb/e11_releve_op/init.do\?identifiant=(?P<identifiant>)'
                               '&typeSolde=(?P<type_solde>)&typeReleve=(?P<type_releve>)&typeDate=(?P<type_date>)'
                               '&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)&ajax=true',
                               '/NCCPresentationWeb/e11_releve_op/init.do', AccountHistoryViewPage)
    account_coming_view = URL('/NCCPresentationWeb/m04_selectionCompteGroupe/init.do\?type=compte&identifiant=(?P<identifiant>)', AccountHistoryViewPage)
    account_history = URL('/NCCPresentationWeb/e11_releve_op/listeOperations.do\?identifiant=(?P<identifiant>)&typeSolde=(?P<type_solde>)&typeReleve=(?P<type_releve>)&typeDate=(?P<type_date>)&dateMin=(?P<date_min>)&dateMax=(?P<date_max>)&ajax=true',
                          '/NCCPresentationWeb/e11_releve_op/listeOperations.do', AccountHistoryPage)
    account_coming = URL('/NCCPresentationWeb/e12_rep_cat_op/listOperations.do\?periode=date_valeur&identifiant=(?P<identifiant>)',
                         '/NCCPresentationWeb/e12_rep_cat_op/listOperations.do', AccountHistoryPage)

    transaction_detail = URL(r'/NCCPresentationWeb/e21/getOptBDDF.do', TransactionPage)
    invest = URL(r'/opcvm/lister-composition/afficher.do', InvestPage)
    # The Market page is used only if there are several market accounts
    market = URL(r'/opcvm/lister-portefeuilles/afficher.do', MarketPage)

    renew_pass = URL('/sommaire/PseRedirectPasswordConnect', ActionNeededPage)

    def __init__(self, config, *args, **kwargs):
        super(BNPEnterprise, self).__init__(config['login'].get(), config['password'].get(), *args, **kwargs)

    def do_login(self):
        self.login.go()

        if not self.login.is_here():
            return

        data = {}
        data['txtAuthentMode'] = 'PASSWORD'
        data['BEFORE_LOGIN_REQUEST'] = None
        data['txtPwdUserId'] = self.username
        data['gridpass_hidden_input'] = self.page.get_password(self.password)

        self.auth.go(data=data)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def iter_accounts(self):
        accounts = []
        # Fetch checking accounts:
        for account in self.accounts.stay_or_go().iter_accounts():
            accounts.append(account)
        # Fetch market accounts:
        try:
            self.market.go()
            if self.market.is_here():
                for market_account in self.page.iter_market_accounts():
                    market_account.parent = find_object(accounts, label=market_account._parent)
                    accounts.append(market_account)

            elif self.invest.is_here():
                # Redirected to invest page, meaning there is only 1 market account.
                # We thus create an Account object for this unique market account.
                account = self.page.get_unique_market_account()
                account.parent = find_object(accounts, label=account._parent)
                accounts.append(account)

        except BrowserForbidden:
            pass

        return accounts

    @need_login
    def get_account(self, _id):
        for account in self.iter_accounts():
            if account.id == _id:
                return account

    @need_login
    def iter_history(self, account):
        # There is no available history for market accounts
        if account.type == Account.TYPE_MARKET:
            return []
        return self._iter_history_base(account)

    @need_login
    def iter_documents(self, subscription):
        raise NotImplementedError()

    @need_login
    def iter_subscription(self):
        raise NotImplementedError()

    def _iter_history_base(self, account):
        dformat = "%Y%m%d"

        # We ask for more 12 months by default, but it may not be supported for somme account types.
        # To avoid duplicated transactions we exit as soon a transaction is not within the expected timeframe
        for date in rrule(MONTHLY, dtstart=(datetime.now() - relativedelta(months=11)), until=datetime.now())[::-1]:

            params = dict(identifiant=account.iban, type_solde='C', type_releve='Previsionnel', type_date='O',
                date_min=(date + relativedelta(days=1) - relativedelta(months=1)).strftime(dformat),
                date_max=date.strftime(dformat)
            )

            self.account_history_view.go(**params)
            self.account_history.go(**params)

            for transaction in sorted_transactions(self.page.iter_history()):
                if transaction._coming:
                    self.logger.debug('skipping coming %r', transaction.to_dict())
                    continue

                if transaction.date > date:
                    self.logger.debug('transaction not within expected timeframe, stop iterating history: %r',
                                      transaction.to_dict())
                    return

                yield transaction

    @need_login
    def iter_coming_operations(self, account):
        # There is no available coming operation for market accounts
        if account.type == Account.TYPE_MARKET:
            return []

        self.account_coming_view.go(identifiant=account.iban)
        self.account_coming.go(identifiant=account.iban)
        return self.page.iter_coming()

    @need_login
    def iter_investment(self, account):
        if account.type != Account.TYPE_MARKET:
            return

        self.market.go()
        # If there is more than one market account, we must fetch the account params:
        if not account._unique:
            if self.market.is_here():
                token = self.page.get_token()
                id_invest = self.page.get_id(label=account.label)
                data = {"numeroCompte": id_invest, "_csrf": token}
                self.location('/opcvm/lister-composition/redirect-afficher.do', data=data)

        for inv in self.page.iter_investment():
            yield inv

    @need_login
    def get_profile(self):
        profile = self.account_history_view.go().get_profile()
        return profile

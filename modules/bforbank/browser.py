# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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
import datetime
from dateutil.relativedelta import relativedelta
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.bank import Account, AccountNotFound
from weboob.capabilities.base import empty
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.decorators import retry
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages import (
    LoginPage, ErrorPage, AccountsPage, HistoryPage, LoanHistoryPage, RibPage,
    LifeInsuranceList, LifeInsuranceIframe, LifeInsuranceRedir,
    BoursePage, CardHistoryPage, CardPage, UserValidationPage, BourseActionNeeded,
)
from .spirica_browser import SpiricaBrowser


class BforbankBrowser(LoginBrowser):
    BASEURL = 'https://client.bforbank.com'

    login = URL(r'/connexion-client/service/login\?urlBack=%2Fespace-client',
                r'/connexion-client/service/login\?urlBack=',
                r'https://secure.bforbank.com/connexion-client/service/login\?urlBack=',
                LoginPage)
    error = URL('/connexion-client/service/auth', ErrorPage)
    user_validation = URL(r'https://client.bforbank.com/profil-client/', UserValidationPage)
    home = URL('/espace-client/$', AccountsPage)
    rib = URL('/espace-client/rib',
              '/espace-client/rib/(?P<id>\d+)', RibPage)
    loan_history = URL('/espace-client/livret/consultation.*', LoanHistoryPage)
    history = URL('/espace-client/consultation/operations/.*', HistoryPage)
    coming = URL(r'/espace-client/consultation/operationsAVenir/(?P<account>\d+)$', HistoryPage)
    card_history = URL('espace-client/consultation/encoursCarte/.*', CardHistoryPage)
    card_page = URL(r'/espace-client/carte/(?P<account>\d+)$', CardPage)

    lifeinsurance_list = URL(r'/client/accounts/lifeInsurance/lifeInsuranceSummary.action', LifeInsuranceList)
    lifeinsurance_iframe = URL(r'https://(?:www|client).bforbank.com/client/accounts/lifeInsurance/consultationDetailSpirica.action', LifeInsuranceIframe)
    lifeinsurance_redir = URL(r'https://assurance-vie.bforbank.com/sylvea/welcomeSSO.xhtml', LifeInsuranceRedir)
    lifeinsurance_error = URL(r'/client/accounts/lifeInsurance/lifeInsuranceError.action\?errorCode=.*&errorMsg=.*',
                              r'https://client.bforbank.com/client/accounts/lifeInsurance/lifeInsuranceError.action\?errorCode=.*&errorMsg=.*',
                              ErrorPage)

    bourse_login = URL(r'/espace-client/titres/debranchementCaTitre/(?P<id>\d+)')
    bourse_action_needed = URL('https://bourse.bforbank.com/netfinca-titres/*', BourseActionNeeded)
    bourse = URL('https://bourse.bforbank.com/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis',
                 'https://bourse.bforbank.com/netfinca-titres/servlet/com.netfinca.frontcr.account.*',
                 BoursePage)
    bourse_titre = URL(r'https://bourse.bforbank.com/netfinca-titres/servlet/com.netfinca.frontcr.navigation.Titre', BoursePage)  # to get logout link

    def __init__(self, birthdate, username, password, *args, **kwargs):
        super(BforbankBrowser, self).__init__(username, password, *args, **kwargs)
        self.birthdate = birthdate
        self.accounts = None
        self.weboob = kwargs['weboob']

        self.spirica = SpiricaBrowser('https://assurance-vie.bforbank.com/',
                                      None, None, *args, **kwargs)

    def deinit(self):
        super(BforbankBrowser, self).deinit()
        self.spirica.deinit()

    def do_login(self):
        if not self.password.isdigit():
            raise BrowserIncorrectPassword()

        self.login.stay_or_go()
        assert self.login.is_here()
        self.page.login(self.birthdate, self.username, self.password)
        if self.error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        if self.accounts is None:
            self.home.stay_or_go()
            accounts = list(self.page.iter_accounts())
            if self.page.RIB_AVAILABLE:
                self.rib.go().populate_rib(accounts)

            self.accounts = []
            for account in accounts:
                self.accounts.append(account)

                if account.type == Account.TYPE_CHECKING:
                    self.card_page.go(account=account.id)
                    if self.page.has_no_card():
                        continue
                    cards = self.page.get_cards(account.id)
                    account._cards = cards
                    if cards:
                        self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/0')
                        indexes = dict(self.page.get_card_indexes())

                    for card in cards:
                        # if there's a credit card (not debit), create a separate, virtual account
                        card.url = account.url
                        card.parent = account
                        card.currency = account.currency
                        card._checking_account = account
                        card._index = indexes[card.number]

                        self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s' % card._index)
                        if self.page.get_debit_date().month == (datetime.date.today() + relativedelta(months=1)).month:
                            self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s?month=1' % card._index)
                        card.balance = 0
                        card.coming = self.page.get_balance()
                        assert not empty(card.coming)

                        # insert it near its companion checking account
                        self.accounts.append(card)

        return iter(self.accounts)

    def _get_card_transactions(self, account):
        self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s?month=1' % account._index)
        assert self.card_history.is_here()
        return self.page.get_operations()

    @need_login
    def get_history(self, account):
        if account.type == Account.TYPE_LOAN:
            return []
        elif account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            bourse_account = self.get_bourse_account(account)
            if not bourse_account:
                return iter([])

            self.location(bourse_account._link_id)
            assert self.bourse.is_here()
            history = list(self.page.iter_history())
            self.leave_espace_bourse()

            return history
        elif account.type == Account.TYPE_LIFE_INSURANCE:
            if not self.goto_spirica(account):
                return iter([])

            return self.spirica.iter_history(account)

        if account.type != Account.TYPE_CARD:
            self.location(account.url.replace('tableauDeBord', 'operations'))
            assert self.history.is_here() or self.loan_history.is_here()
            transactions_list = []
            if account.type == Account.TYPE_CHECKING:
                # transaction of the day
                for tr in self.page.get_today_operations():
                    transactions_list.append(tr)
            # history
            for tr in self.page.get_operations():
                transactions_list.append(tr)

            return sorted_transactions(transactions_list)
        else:
            # for summary transactions, the transactions must be on both accounts:
            # negative amount on checking account, positive on card account
            transactions = []
            self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s?month=1' % account._index)
            if self.page.get_debit_date().month == (datetime.date.today() - relativedelta(months=1)).month:
                transactions = list(self.page.get_operations())
                summary = self.page.create_summary()
                if summary:
                    transactions.insert(0, summary)
            return transactions

    @need_login
    def get_coming(self, account):
        if account.type == Account.TYPE_CHECKING:
            self.coming.go(account=account.id)
            return self.page.get_operations()
        elif account.type == Account.TYPE_CARD:
            self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s' % account._index)
            transactions = list(self.page.get_operations())
            if self.page.get_debit_date().month == (datetime.date.today() + relativedelta(months=1)).month:
                self.location(account.url.replace('tableauDeBord', 'encoursCarte') + '/%s?month=1' % account._index)
                transactions += list(self.page.get_operations())
            return sorted_transactions(transactions)
        else:
            raise NotImplementedError()


    def goto_lifeinsurance(self, account):
        self.location('https://client.bforbank.com/espace-client/assuranceVie')
        self.lifeinsurance_list.go()

    @retry(AccountNotFound, tries=5)
    def goto_spirica(self, account):
        assert account.type == Account.TYPE_LIFE_INSURANCE
        self.goto_lifeinsurance(account)

        if self.login.is_here():
            self.logger.info('was logged out, relogging')
            # if we don't clear cookies, we may land on the wrong spirica page
            self.session.cookies.clear()
            self.spirica.session.cookies.clear()

            self.do_login()
            self.goto_lifeinsurance(account)

        if self.lifeinsurance_list.is_here():
            self.logger.debug('multiple life insurances, searching for %r', account)
            # multiple life insurances: dedicated page to choose
            for insurance_account in self.page.iter_accounts():
                self.logger.debug('testing %r', account)
                if insurance_account.id == account.id:
                    self.location(insurance_account.url)
                    assert self.lifeinsurance_iframe.is_here()
                    break
            else:
                raise AccountNotFound('account was not found in the dedicated page')
        else:
            assert self.lifeinsurance_iframe.is_here()

        self.location(self.page.get_iframe())
        if self.lifeinsurance_error.is_here():
            self.home.go()
            self.logger.warning('life insurance site is unavailable')
            return False

        assert self.lifeinsurance_redir.is_here()

        redir = self.page.get_redir()
        assert redir
        account.url = self.absurl(redir)
        self.spirica.session.cookies.update(self.session.cookies)
        self.spirica.logged = True
        return True

    def get_bourse_account(self, account):
        self.bourse_login.go(id=account.id)  # "login" to bourse page

        self.bourse.go()
        assert self.bourse.is_here()

        if self.page.password_required():
            return
        self.logger.debug('searching account matching %r', account)
        for bourse_account in self.page.get_list():
            self.logger.debug('iterating account %r', bourse_account)
            if bourse_account.id.startswith(account.id[3:]):
                return bourse_account
        else:
            raise AccountNotFound()

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            if not self.goto_spirica(account):
                return iter([])

            return self.spirica.iter_investment(account)
        elif account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            bourse_account = self.get_bourse_account(account)
            if not bourse_account:
                return iter([])

            self.location(bourse_account._market_link)
            assert self.bourse.is_here()
            invs = list(self.page.iter_investment())
            # _especes is set during BoursePage accounts parsing. BoursePage
            # inherits from lcl module BoursePage
            if bourse_account._especes:
                invs.append(create_french_liquidity(bourse_account._especes))

            self.leave_espace_bourse()

            return invs

        raise NotImplementedError()

    def leave_espace_bourse(self):
        # To enter the Espace Bourse from the standard Espace Client,
        # you need to logout first from the Espace Bourse, otherwise
        # a 500 ServerError is returned.
        # Typically needed between iter_history and iter_investments when dealing
        # with a market or PEA account, or when running them twice in a row
        if self.bourse.is_here():
            self.location(self.bourse_titre.build())
            self.location(self.page.get_logout_link())
            self.do_login()

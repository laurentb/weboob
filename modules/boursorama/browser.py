# -*- coding: utf-8 -*-

# Copyright(C) 2016       Baptiste Delpey
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


from datetime import date
from dateutil.relativedelta import relativedelta

from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account

from .pages import LoginPage, VirtKeyboardPage, AccountsPage, AsvPage, CardPage, HistoryPage, AccbisPage, AuthenticationPage,\
                   MarketPage, LoanPage


__all__ = ['BoursoramaBrowser']


class BrowserIncorrectAuthenticationCode(BrowserIncorrectPassword):
    pass


class BoursoramaBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://clients.boursorama.com'

    keyboard = URL('/connexion/clavier-virtuel\?_hinclude=300000', VirtKeyboardPage)
    login = URL('/connexion/\?clean=1', LoginPage)
    accounts = URL('/dashboard/comptes\?_hinclude=300000', AccountsPage)
    acc_tit = URL('/comptes/titulaire/(?P<webid>.*)\?_hinclude=1', AccbisPage)
    acc_rep = URL('/comptes/representative/(?P<webid>.*)\?_hinclude=1', AccbisPage)
    history = URL('/compte/(cav|epargne)/(?P<webid>.*)/mouvements.*', HistoryPage)
    card_transactions = URL('budget/mouvements.*', HistoryPage)
    budget_transactions = URL('/budget/compte/(?P<webid>.*)/mouvements.*', HistoryPage)
    other_transactions = URL('/compte/cav/(?P<webid>.*)/mouvements.*', HistoryPage)
    asv = URL('/compte/assurance-vie/.*', AsvPage)
    market = URL('/compte/(?!assurance|cav|epargne).*/(positions|mouvements)', MarketPage)
    cards = URL('/compte/cav/.*/limite.*', CardPage)
    loans = URL('/credit/immobilier/.*/informations', LoanPage)
    authentication = URL('/securisation', AuthenticationPage)


    __states__ = ('auth_token',)

    def __init__(self, config=None, *args, **kwargs):
        self.config = config
        self.auth_token = None
        self.webid = None
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(BoursoramaBrowser, self).__init__(*args, **kwargs)

    def handle_authentication(self):
        if self.authentication.is_here():
            if self.config['enable_twofactors'].get():
                self.page.sms_first_step()
                self.page.sms_second_step()
            else:
                raise BrowserIncorrectAuthenticationCode(
                    """Boursorama - activate the two factor authentication in boursorama config."""
                    """ You will receive SMS code but are limited in request per day (around 15)"""
                )

    def do_login(self):
        assert isinstance(self.config['device'].get(), basestring)
        assert isinstance(self.config['enable_twofactors'].get(), bool)
        assert self.password.isdigit()

        if self.auth_token and self.config['pin_code'].get():
            self.page.authenticate()
        else:
            self.login.stay_or_go()
            self.page.login(self.username, self.password)

            if self.login.is_here():
                raise BrowserIncorrectPassword()

            # After login, we might be redirected to the two factor authentication page.
            self.handle_authentication()

        if self.login.is_here():
            raise BrowserIncorrectAuthenticationCode('Invalid PIN code')


    @need_login
    def get_accounts_list(self):
        accounts = list()
        cards_scrapped = None
        for account in self.accounts.go().iter_accounts():
            accounts.append(account)
        for account in list(accounts):
            if account._card and not cards_scrapped:
                self.location(account._card)
                for card in self.page.iter_accounts():
                    accounts.append(card)
                cards_scrapped = True
        self.acc_tit.go(webid=self.webid).populate(list(accounts))
        if not all([hasattr(acc, '_webid') for acc in accounts]):
            self.acc_rep.go(webid=self.webid).populate(list(accounts))
        return iter(accounts)

    @need_login
    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a
        return None

    @need_login
    def get_history(self, account):
        if not account._history_page:
            return
        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            self.location('%s/mouvements' % account._history_page)
            for t in self.page.iter_history():
                yield t
        else:
            # We look for 1 year of history.
            params = {}
            params['movementSearch[toDate]'] = (date.today() + relativedelta(days=40)).strftime('%d/%m/%Y')
            params['movementSearch[fromDate]'] = (date.today() - relativedelta(years=1)).strftime('%d/%m/%Y')
            params['movementSearch[selectedAccounts][]'] = account._webid
            if account.type != Account.TYPE_CARD:
                account._history_page.go(webid=account._webid, params=params)
            else:
                self.card_transactions.go(params=params)
            for t in self.page.iter_history():
                yield t

    @need_login
    def get_investment(self, account):
        if not account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            raise NotImplementedError()
        self.location(account._link)
        return self.page.iter_investment()

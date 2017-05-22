# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

import re

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account
from weboob.capabilities.base import empty

from .pages import LoginPage, AccountsPage, TransactionsPage, AVAccountPage, AVHistoryPage, FormPage


__all__ = ['GanAssurances']


class GanAssurances(LoginBrowser):
    login = URL('/wps/portal/login.*',
                'https://authentification.(ganassurances|ganpatrimoine).fr/cas/login.*',
                '/wps/portal/inscription.*', LoginPage)
    accounts = URL('/wps/myportal/TableauDeBord', AccountsPage)
    transactions = URL('/wps/myportal/!ut.*', TransactionsPage)
    av_account_form = URL('/wps/myportal/assurancevie/rivage/!ut/p/a1/.*', FormPage)
    av_account = URL('https://secure-rivage.(ganassurances|ganpatrimoine).fr/contratVie.rivage.syntheseContratEparUc.gsi', AVAccountPage)
    av_history = URL('https://secure-rivage.(?P<website>.*).fr/contratVie.rivage.mesOperations.gsi', AVHistoryPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'https://%s' % website
        self.website = re.findall('espaceclient.(.*?).fr', self.BASEURL)[0]

        super(GanAssurances, self).__init__(*args, **kwargs)

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.accounts.go()

        assert(self.login.is_here())

        self.page.login(self.username, self.password)

        if self.login.is_here() or '/login' in self.url:
            # sometimes ganassurances may be redirected to groupama.../login
            raise BrowserIncorrectPassword()

    # For life asssurance accounts, to get balance we use the link from the account.
    # And to get history (or other) we need to use the link again but the link works only once.
    # So we get balance only for iter_account to not use the new link each time.
    @need_login
    def get_accounts_list(self, balance=True):
        self.accounts.stay_or_go()
        a = self.page.get_list()
        for account in a:
            if account.type == Account.TYPE_LIFE_INSURANCE and balance:
                assert empty(account.balance)
                self.location(account._link)
                self.page.av_account_form()
                account.balance = self.page.get_av_balance()
                self.location(self.BASEURL)
        return a

    def get_history(self, account):
        accounts = self.get_accounts_list(balance=False)
        for a in accounts:
            if a.id == account.id:
                self.location(a._link)
                if a.type == Account.TYPE_LIFE_INSURANCE:
                    self.page.av_account_form()
                    self.av_history.go(website=self.website)
                    return self.page.get_av_history()
                assert self.transactions.is_here()
                return self.page.get_history(accid=account.id)
        return iter([])

    def get_coming(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            return iter([])
        accounts = self.get_accounts_list()
        for a in accounts:
            if a.id == account.id:
                self.location(a._link)
                assert self.transactions.is_here()

                link = self.page.get_coming_link()
                if link is not None:
                    self.location(self.page.get_coming_link())
                    assert self.transactions.is_here()

                    return self.page.get_history(accid=account.id)

        return iter([])

    def get_investment(self, account):
        if account.type != Account.TYPE_LIFE_INSURANCE:
            return iter([])
        accounts = self.get_accounts_list(balance=False)
        for a in accounts:
            if a.id == account.id:
                self.location(a._link)
                self.page.av_account_form()
                return self.page.get_av_investments()

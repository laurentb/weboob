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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account
from weboob.capabilities.base import empty

from .pages import LoginPage, AccountsPage, TransactionsPage, AVAccountPage, AVHistoryPage, FormPage


__all__ = ['GroupamaBrowser']


class GroupamaBrowser(LoginBrowser):
    BASEURL = 'https://espaceclient.groupama.fr'

    login = URL('/wps/portal/login',
                'https://authentification.(ganassurances|ganpatrimoine|groupama).fr/cas/login',
                '/wps/portal/inscription', LoginPage)
    accounts = URL('/wps/myportal/TableauDeBord', AccountsPage)
    transactions = URL('/wps/myportal/!ut', TransactionsPage)
    av_account_form = URL('/wps/myportal/assurancevie/', FormPage)
    av_account = URL('https://secure-rivage.(ganassurances|ganpatrimoine|groupama).fr/contratVie.rivage.syntheseContratEparUc.gsi', AVAccountPage)
    av_history = URL('https://secure-rivage.(?P<website>.*).fr/contratVie.rivage.mesOperations.gsi', AVHistoryPage)

    def __init__(self, *args, **kwargs):
        super(GroupamaBrowser, self).__init__(*args, **kwargs)
        self.website = 'groupama'

    def do_login(self):
        self.login.stay_or_go()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    # For life asssurance accounts, to get balance we use the link from the account.
    # And to get history (or other) we need to use the link again but the link works only once.
    # So we get balance only for iter_account to not use the new link each time.
    @need_login
    def get_accounts_list(self, balance=True):
        accounts = []
        self.accounts.stay_or_go()
        for account in self.page.get_list():
            if account.type == Account.TYPE_LIFE_INSURANCE and balance:
                assert empty(account.balance)
                self.location(account._link)
                if self.av_account_form.is_here():
                    self.page.av_account_form()
                    account.balance, account.currency = self.page.get_av_balance()
                self.location(self.BASEURL)
            if account.balance or not balance:
                accounts.append(account)
        return accounts

    def _get_history(self, account):
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

    # Duplicate line in case of arbitration because the site has only one line for the 2 transactions (debit and credit on the same line)
    def get_history(self, account):
        for tr in self._get_history(account):
            yield tr
            if getattr(tr, '_arbitration', False):
                tr = tr.copy()
                tr.amount = -tr.amount
                yield tr

    def get_coming(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            return iter([])
        for a in self.get_accounts_list():
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
        for a in self.get_accounts_list(balance=False):
            if a.id == account.id:
                self.location(a._link)
                self.page.av_account_form()
                if self.av_account.is_here():
                    return self.page.get_av_investments()
        return iter([])

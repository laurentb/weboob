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


import ssl

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from weboob.capabilities.bank import Account
from weboob.capabilities.base import NotAvailable

from .pages import LoginPage, AccountsPage, AccountDetailsPage, TransactionsPage


__all__ = ['GroupamaBrowser']


class GroupamaBrowser(LoginBrowser):
    BASEURL = 'https://espaceclient.groupama.fr'

    login = URL('/wps/portal/login',
                '/wps/portal/inscription', LoginPage)
    accounts = URL('/wps/myportal/TableauDeBord', AccountsPage)
    # for life insurance accounts
    account_details = URL('/wps/myportal/assurancevie/',
                          'https://secure-rivage.groupama.fr/', AccountDetailsPage)
    transactions = URL('/wps/myportal/!ut.*', TransactionsPage)

    def prepare_request(self, req):
        """
        Gan Assurances does not support SSL anymore.
        """
        preq = super(GroupamaBrowser, self).prepare_request(req)
        conn = self.session.adapters['https://'].get_connection(preq.url)
        conn.ssl_version = ssl.PROTOCOL_TLSv1
        return preq

    def do_login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.login.stay_or_go()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.accounts.stay_or_go()
        assert self.accounts.is_here()

        accounts_list = [a for a in self.page.get_list()]

        for account in accounts_list[:]:
            if account.type is Account.TYPE_LIFE_INSURANCE:
                self.get_account_details(account)
            elif account.balance is NotAvailable:
                accounts_list.remove(account)

        return accounts_list

    @need_login
    def get_account_details(self, account):
        if account._link:
            self.location(account._link)

            if self.account_details.is_here():
                rivage = self.page.get_rivage()

                if rivage is not None:
                    self.location(rivage.get('link'), data=rivage.get('data'))
                    self.page.fill_rivage_account_details(account)
                else:
                    self.page.fill_account_details(account)
        self.accounts.stay_or_go()

    @need_login
    def get_history(self, account):
        if account.type != Account.TYPE_LIFE_INSURANCE:
            accounts_list = self.get_accounts_list()

            for a in accounts_list:
                if a.id == account.id:
                    self.location(a._link)
                    assert self.transactions.is_here()

                    return self.page.get_history(accid=account.id)
        return iter([])

    @need_login
    def get_coming(self, account):
        if account.type != Account.TYPE_LIFE_INSURANCE:
            accounts_list = self.get_accounts_list()

            for a in accounts_list:
                if a.id == account.id:
                    self.location(a._link)
                    assert self.transactions.is_here()

                    link = self.page.get_coming_link()

                    if link is not None:
                        self.location(self.page.get_coming_link())
                        assert self.transactions.is_here()

                        return self.page.get_history(accid=account.id)
        return iter([])

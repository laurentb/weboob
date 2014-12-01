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

from .pages import LoginPage, AccountsPage, TransactionsPage


__all__ = ['GanAssurances']


class GanAssurances(LoginBrowser):
    login = URL('/wps/portal/login.*', LoginPage)
    accounts = URL('/wps/myportal/TableauDeBord', AccountsPage)
    transactions = URL('/wps/myportal/!ut.*', TransactionsPage)

    def __init__(self, website, *args, **kwargs):
        self.BASEURL = 'https://%s' % website
        super(GanAssurances, self).__init__(*args, **kwargs)

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
        return self.page.get_list()

    def get_history(self, account):
        accounts = self.get_accounts_list()
        for a in accounts:
            if a.id == account.id:
                self.location(a._link)
                assert self.transactions.is_here()
                return self.page.get_history()

        return iter([])


    def get_coming(self, account):
        accounts = self.get_accounts_list()
        for a in accounts:
            if a.id == account.id:
                self.location(a._link)
                assert self.transactions.is_here()

                self.location(self.page.get_coming_link())
                assert self.transactions.is_here()

                return self.page.get_history()

        return iter([])

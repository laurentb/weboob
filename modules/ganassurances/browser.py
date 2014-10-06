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


from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, TransactionsPage


__all__ = ['GanAssurances']


class GanAssurances(Browser):
    PROTOCOL = 'https'
    PAGES = {'https://[^/]+/wps/portal/login.*':         LoginPage,
             'https://[^/]+/wps/myportal/TableauDeBord': AccountsPage,
             'https://[^/]+/wps/myportal/!ut.*':         TransactionsPage,
            }

    def __init__(self, website, *args, **kwargs):
        self.DOMAIN = website
        Browser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        self.location('/wps/myportal/TableauDeBord')

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.is_logged():
            return

        if not self.is_on_page(LoginPage):
            self.home()

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('/wps/myportal/TableauDeBord')
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if account._link is None:
            return iter([])

        self.location(account._link)
        assert self.is_on_page(TransactionsPage)

        return self.page.get_history()

    def get_coming(self, account):
        if account._link is None:
            return iter([])

        self.location(account._link)
        assert self.is_on_page(TransactionsPage)

        self.location(self.page.get_coming_link())
        assert self.is_on_page(TransactionsPage)

        return self.page.get_history()

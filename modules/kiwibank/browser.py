# -*- coding: utf-8 -*-

# Copyright(C) 2015 Cédric Félizard
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword
from .pages import LoginPage, AccountPage, HistoryPage


__all__ = ['Kiwibank']


class HistoryUnavailable(Exception):
    pass


class Kiwibank(LoginBrowser):
    BASEURL = 'https://www.ib.kiwibank.co.nz/mobile/'
    TIMEOUT = 30

    login = URL('login/', LoginPage)
    login_error = URL('login-error/', LoginPage)
    accounts = URL('accounts/$', AccountPage)
    account = URL('/accounts/view/[0-9A-F]+$', HistoryPage)

    def do_login(self):
        self.login.stay_or_go()
        self.page.login(self.username, self.password)

        if self.login.is_here() or self.login_error.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts(self):
        self.accounts.stay_or_go()
        return self.page.get_accounts()

    @need_login
    def get_history(self, account):
        if account._link is None:
            raise HistoryUnavailable()

        self.location(account._link)

        return self.page.get_history()

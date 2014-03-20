# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014  Fourcot Florent
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


from weboob.tools.browser2 import LoginBrowser, URL, need_login
from weboob.tools.browser import BrowserBanned, BrowserIncorrectPassword
from .pages import HomePage, LoginPage, HistoryPage, BillsPage, ErrorPage

__all__ = ['PoivyBrowser']


class PoivyBrowser(LoginBrowser):
    BASEURL = 'https://www.poivy.com'

    login = URL('/login', LoginPage)
    homepage = URL('/buy_credit.*', HomePage)
    history = URL('/recent_calls', HistoryPage)
    bills = URL('/purchases', BillsPage)
    warning = URL('/warning.*', ErrorPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        self.login.stay_or_go()

        if not self.page.login(self.username, self.password):
            raise BrowserBanned('Too many connections from you IP address: captcha enabled')

        if self.login.is_here() or self.warning.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_subscription_list(self):
        return self.homepage.stay_or_go().get_list()

    def _find_id_list(self, mylist, _id):
        for a in mylist:
            if a.id == _id:
                return a
        return None

    @need_login
    def get_subscription(self, _id):
        return self._find_id_list(self.get_subscription_list(), _id)

    @need_login
    def get_history(self):
        return self.history.stay_or_go().get_calls()

    @need_login
    def iter_bills(self, parentid):
        return self.bills.stay_or_go().get_bills()

    @need_login
    def get_bill(self, _id):
        return self._find_id_list(self.iter_bills(), _id)

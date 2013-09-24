# -*- coding: utf-8 -*-

# Copyright(C) 2013  Fourcot Florent
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword, BrowserBanned
from .pages import HomePage, LoginPage, HistoryPage, BillsPage, ErrorPage

__all__ = ['PoivyBrowser']


class PoivyBrowser(BaseBrowser):
    DOMAIN = 'www.poivy.com'
    PROTOCOL = 'https'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*login':                 LoginPage,
             '.*buy_credit.*':            HomePage,
             '.*/recent_calls':         HistoryPage,
             '.*purchases':             BillsPage,
             '.*warning.*':             ErrorPage
             }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('/login')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('/login')

        if not self.page.login(self.username, self.password):
            raise BrowserBanned('Too many connections from you IP address: captcha enabled')

        if self.is_on_page(LoginPage) or self.is_on_page(ErrorPage):
            raise BrowserIncorrectPassword()

    def get_subscription_list(self):
        if not self.is_on_page(HomePage):
            self.location('/buy_credit')

        return self.page.get_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)

        l = self.get_subscription_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self):
        if not self.is_on_page(HistoryPage):
            self.location('/recent_calls')
        return self.page.get_calls()

    def iter_bills(self, parentid):
        if not self.is_on_page(BillsPage):
            self.location('/purchases')
        return self.page.date_bills()

    def get_bill(self, id):
        assert isinstance(id, basestring)

        l = self.iter_bills(id)
        for a in l:
            if a.id == id:
                return a

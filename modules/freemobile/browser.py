# -*- coding: utf-8 -*-

# Copyright(C) 2012  Romain Bignon
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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from .pages import HomePage, LoginPage, HistoryPage, DetailsPage

__all__ = ['Freemobile']


class Freemobile(BaseBrowser):
    DOMAIN = 'mobile.free.fr'
    PROTOCOL = 'https'
    CERTHASH = '73d1205c91dc6188597399e718ee145d9f1287fcc290a31ff0ba4477fbc893b2'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*moncompte/index.php': LoginPage,
             '.*page=home':           HomePage,
             '.*page=suiviconso':     DetailsPage,
             '.*page=consotel_current_month': HistoryPage
            }
    #DEBUG_HTTP = True

    def home(self):
        self.location('https://mobile.free.fr/moncompte/index.php')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.username.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://mobile.free.fr/moncompte/index.php')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_subscription_list(self):
        if not self.is_on_page(HomePage):
            self.location('/moncompte/index.php?page=home')

        return self.page.get_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(HomePage):
            self.location('/moncompte/index.php?page=home')

        for a in self.get_subscription_list():
            if a.id == id:
                return a

        return None

    def get_history(self, subscription):
        if not self.is_on_page(HistoryPage):
            self.location('/moncompte/ajax.php?page=consotel_current_month', 'login=' + subscription._login)
        return self.page.get_calls(subscription)

    def get_details(self, subscription):
        if not self.is_on_page(DetailsPage):
            self.location('/moncompte/index.php?page=suiviconso')
        return self.page.get_details(subscription)

    def iter_bills(self, parentid):
        if not self.is_on_page(DetailsPage):
            self.location('/moncompte/index.php?page=suiviconso')
        return self.page.date_bills()

    def get_bill(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(DetailsPage):
            self.location('/moncompte/index.php?page=suiviconso')
        l = self.page.date_bills()
        for a in l:
            if a.id == id:
                return a

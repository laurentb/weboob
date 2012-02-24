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
from .pages import HomePage, LoginPage, HistoryPage

__all__ = ['Freemobile']


class Freemobile(BaseBrowser):
    DOMAIN = 'mobile.free.fr'
    PROTOCOL = 'https'
    ENCODING =  None # refer to the HTML encoding
    PAGES = {'.*moncompte/index.php':   LoginPage,
             '.*page=home':            HomePage,
             '.*page=suiviconso':         HistoryPage
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

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

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    # XXX : not implemented
    def get_history(self):
        if not self.is_on_page(HistoryPage):
            self.location('/moncompte/index.php?page=suiviconso')
        return self.page.get_calls()

    def get_details(self):
        if not self.is_on_page(HistoryPage):
            self.location('/moncompte/index.php?page=suiviconso')
        test = self.page.get_details()
        return test

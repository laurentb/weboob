# -*- coding: utf-8 -*-

# Copyright(C) 2012  Fourcot Florent
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
from .pages import HomePage, LoginPage, HistoryPage, DetailsPage, BillsPage

__all__ = ['Nettokom']


class Nettokom(Browser):
    DOMAIN = 'konto.nettokom.de'
    PROTOCOL = 'https'
    ENCODING = None  # refer to the HTML encoding
    PAGES = {'.*login.html.*': LoginPage,
             '.*start.html':           HomePage,
             '.*guthabenverbrauch.html':     DetailsPage,
             '.*/verbindungsnachweis/.*': HistoryPage,
             '.*verbindungsnachweis.html': BillsPage
            }

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('/start.html')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.username.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('/login.html')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_subscription_list(self):
        if not self.is_on_page(HomePage):
            self.location('/start.html')

        return self.page.get_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(HomePage):
            self.location('/start.html')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self):
        if not self.is_on_page(HistoryPage):
            self.location('/verbindungsnachweis/alle-verbindungen.html')
        return self.page.get_calls()

    def get_details(self):
        if not self.is_on_page(DetailsPage):
            self.location('/guthabenverbrauch.html')
        return self.page.get_details()

    def iter_documents(self, parentid):
        if not self.is_on_page(BillsPage):
            self.location('/verbindungsnachweis.html')
        return self.page.date_bills()

    def get_document(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(BillsPage):
            self.location('/verbindungsnachweis.html')
        l = self.page.date_bills()
        for a in l:
            if a.id == id:
                return a

# Todo : url depends of file format
#    def download_document(self, id):
#        assert isinstance(id, basestring)
#        date = id.split('.')[1]
#
#        return self.readurl('/moncompte/ajax.php?page=facture&mode=html&date=' + date)

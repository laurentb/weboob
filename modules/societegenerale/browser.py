# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

from .pages.accounts_list import AccountsList, AccountHistory
from .pages.login import LoginPage, BadLoginPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(BaseBrowser):
    DOMAIN_LOGIN = 'particuliers.societegenerale.fr'
    DOMAIN = 'particuliers.secure.societegenerale.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
             'https://particuliers.societegenerale.fr/.*':  LoginPage,
             'https://.*.societegenerale.fr//acces/authlgn.html': BadLoginPage,
             '.*restitution/cns_listeprestation.html':      AccountsList,
             '.*restitution/cns_detailCav.html.*':          AccountHistory,
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

        self.page.login(self.username, self.password)

        if self.is_on_page(LoginPage) or \
           self.is_on_page(BadLoginPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def iter_history(self, url):
        self.location(url)

        assert self.is_on_page(AccountHistory)
        #self.location(self.page.get_part_url())

        #assert self.is_on_page(AccountHistoryPart)
        return self.page.iter_transactions()

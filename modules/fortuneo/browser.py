# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


from weboob.tools.browser import BaseBrowser #, BrowserIncorrectPassword

from .pages.login import LoginPage
from .pages.accounts_list import AccountsList, AccountHistoryPage

__all__ = ['Fortuneo']

class Fortuneo(BaseBrowser):
    DOMAIN_LOGIN = 'www.fortuneo.fr'
    DOMAIN = 'www.fortuneo.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
            '.*identification.jsp.*':
                    LoginPage,
            '.*/prive/mes-comptes/synthese-tous-comptes\.jsp.*':
                    AccountsList,
            '.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp\?COMPTE_ACTIF=.*':
                    AccountHistoryPage
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        """main page (login)"""
        self.location('/fr/prive/identification.jsp')

    def is_logged(self):
        """Return True if we are logged on website"""

        if self.is_on_page(AccountHistoryPage) or self.is_on_page(AccountsList):
            return True
        else:
            return False

    def login(self):
        """Login to the website.
        This function is called when is_logged() returns False and the
        password attribute is not None."""

        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/fr/identification.jsp')

        self.page.login(self.username, self.password)
        self.location('/fr/prive/mes-comptes/synthese-tous-comptes.jsp')

    def get_history(self, account):
        if not self.is_on_page(AccountHistoryPage):
            self.location(account._link_id)
        return self.page.get_operations(account)

    def get_accounts_list(self):
        """accounts list"""

        if not self.is_on_page(AccountsList):
            self.location('/fr/prive/mes-comptes/synthese-tous-comptes.jsp')

        return self.page.get_list()

    def get_account(self, id):
        """Get an account from its ID"""
        assert isinstance(id, basestring)
        l = self.get_accounts_list()

        for a in l:
            if a.id == id:
                return a

        return None

# vim:ts=4:sw=4

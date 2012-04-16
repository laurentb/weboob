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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages.accounts_list import AccountHistory #AccountsList, IndexPage
from .pages.login import LoginPage #, BadLoginPage


__all__ = ['Fortuneo']

# https://www.fortuneo.fr/fr/prive/mes-comptes/livret/consulter-situation/consulter-solde.jsp?COMPTE_ACTIF=FT00991337
class Fortuneo(BaseBrowser):
    DOMAIN_LOGIN = 'www.fortuneo.fr'
    DOMAIN = 'www.fortuneo.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
            '.*identification.jsp.*':                                                 LoginPage,
            #'.*/prive/default.jsp.*':                                         IndexPage,
            #'.*/prive/default.jsp.*':                                         AccountsList,
            '.*/prive/default.jsp.*':                                         AccountHistory,
            #'https://www.fortuneo.fr/fr/identification.jsp':                         BadLoginPage,
            #'.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp.*': AccountsList,
            #'.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp.*': AccountHistory,
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('/fr/prive/identification.jsp')
        #self.location('https://' + self.DOMAIN_LOGIN + '/fr/identification.jsp')
        #self.location('https://' + self.DOMAIN_LOGIN + '/fr/prive/mes-comptes/synthese-tous-comptes.jsp')

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        #assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/fr/identification.jsp')

        self.page.login(self.username, self.password)

        #if self.is_on_page(LoginPage) or \
        #   self.is_on_page(BadLoginPage):
        #    raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsList):
            self.location('/fr/prive/default.jsp?ANav=1')
            #self.location('')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(AccountsList):
            self.location('/fr/prive/default.jsp?ANav=1')

	print "\n\n\n", self.page, "\n\n\n"
        #l = self.page.get_list()
        #for a in l:
        #    if a.id == id:
        #        return a

        return None

    def iter_history(self, url):
        self.location(url)

        if not self.is_on_page(AccountHistory):
            # TODO: support other kind of accounts
            return iter([])

        return self.page.iter_transactions()

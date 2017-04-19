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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages.login import LoginPage
from .pages.accounts_list import GlobalAccountsList, AccountsList, AccountHistoryPage, CardHistoryPage, \
                                 InvestmentHistoryPage, PeaHistoryPage

__all__ = ['Fortuneo']


class Fortuneo(LoginBrowser):
    BASEURL = 'https://mabanque.fortuneo.fr'
    #CERTHASH = ['4ff0301115f80f18c4e81a136ca28829b46d416d404174945b1ae48abd0634e2', '608d63d9ef394c13a64b71ed55e4564491873498dd62540a6b7f7b88f251be30']
    login_page = URL(r'.*identification\.jsp.*', LoginPage)

    accounts_page = URL(r'.*prive/default\.jsp.*',
                        r'.*/prive/mes-comptes/synthese-mes-comptes\.jsp',
                        AccountsList)
    global_accounts = URL(r'.*/prive/mes-comptes/synthese-globale/synthese-mes-comptes\.jsp', GlobalAccountsList)

    account_history = URL(r'.*/prive/mes-comptes/livret/consulter-situation/consulter-solde\.jsp.*',
                          r'.*/prive/mes-comptes/compte-courant/consulter-situation/consulter-solde\.jsp.*',
                          r'.*/prive/mes-comptes/compte-especes.*',
                          AccountHistoryPage)
    card_history = URL(r'.*/prive/mes-comptes/compte-courant/carte-bancaire/encours-debit-differe\.jsp.*', CardHistoryPage)
    pea_history = URL(r'.*/prive/mes-comptes/compte-titres-.*', r'.*/prive/mes-comptes/pea.*', PeaHistoryPage)
    invest_history = URL(r'.*/prive/mes-comptes/assurance-vie.*', InvestmentHistoryPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.login_page.is_here():
            self.location('/fr/identification.jsp')

        self.page.login(self.username, self.password)

        if self.login_page.is_here():
            raise BrowserIncorrectPassword()

        self.location('/fr/prive/mes-comptes/synthese-mes-comptes.jsp')

        if self.accounts_page.is_here() and self.page.need_reload():
            self.location('/ReloadContext?action=1&')
        elif self.accounts_page.is_here() and self.page.need_sms():
            raise BrowserIncorrectPassword('Authentification with sms is not supported')

    @need_login
    def get_investments(self, account):
        self.location(account.url)

        return self.page.get_investments(account)

    @need_login
    def get_history(self, account):
        self.location(account.url)

        if self.page.select_period():
            return self.page.get_operations(account)

        return iter([])

    @need_login
    def get_coming(self, account):
        for cb_link in account._card_links:
            self.location(cb_link)

            for tr in self.page.get_operations(account):
                yield tr

    @need_login
    def get_accounts_list(self):
        """accounts list"""

        if not self.accounts_page.is_here():
            self.location('/fr/prive/mes-comptes/synthese-mes-comptes.jsp')

        return self.page.get_list()

    @need_login
    def get_account(self, id):
        """Get an account from its ID"""

        assert isinstance(id, basestring)
        for a in list(self.get_accounts_list()):
            if a.id == id:
                return a

        return None

# vim:ts=4:sw=4

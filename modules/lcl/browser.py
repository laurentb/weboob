# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon, Pierre Mazière
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


from urlparse import urlsplit, parse_qsl

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import SkipPage, LoginPage, AccountsPage, AccountHistoryPage, \
                   CBListPage, CBHistoryPage, ContractsPage


__all__ = ['LCLBrowser']


# Browser
class LCLBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'particuliers.secure.lcl.fr'
    CERTHASH = ['ddfafa91c3e4dba2e6730df723ab5559ae55db351307ea1190d09bd025f74cce', '430814d3713cf2556e74749335e9d7ad8bb2a9350a1969ee539d1e9e9492a59a', 'ee395a71a777286091345a9ae55df699cf830bbc218faf71f08ce198d30543a3']
    ENCODING = 'utf-8'
    USER_AGENT = BaseBrowser.USER_AGENTS['wget']
    PAGES = {
        'https://particuliers.secure.lcl.fr/outil/UAUT/Authentication/authenticate': LoginPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT\?from=.*': LoginPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT/Accueil/preRoutageLogin': LoginPage,
        'https://particuliers.secure.lcl.fr//outil/UAUT/Contract/routing': LoginPage,
        'https://particuliers.secure.lcl.fr/outil/UWER/Accueil/majicER': LoginPage,
        'https://particuliers.secure.lcl.fr/outil/UWER/Enregistrement/forwardAcc': LoginPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT/Contrat/choixContrat.*': ContractsPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT/Contract/getContract.*': ContractsPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT/Contract/selectContracts.*': ContractsPage,
        'https://particuliers.secure.lcl.fr/outil/UWSP/Synthese': AccountsPage,
        'https://particuliers.secure.lcl.fr/outil/UWLM/ListeMouvements.*/accesListeMouvements.*': AccountHistoryPage,
        'https://particuliers.secure.lcl.fr/outil/UWCB/UWCBEncours.*/listeCBCompte.*': CBListPage,
        'https://particuliers.secure.lcl.fr/outil/UWCB/UWCBEncours.*/listeOperations.*': CBHistoryPage,
        'https://particuliers.secure.lcl.fr/outil/UAUT/Contrat/selectionnerContrat.*': SkipPage,
        'https://particuliers.secure.lcl.fr/index.html': SkipPage
        }

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(LoginPage):
            self.location('%s://%s/outil/UAUT/Authentication/authenticate'
                          % (self.PROTOCOL, self.DOMAIN),
                          no_login=True)

        if not self.page.login(self.username, self.password) or \
           (self.is_on_page(LoginPage) and self.page.is_error()) :
            raise BrowserIncorrectPassword("invalid login/password.\nIf you did not change anything, be sure to check for password renewal request\non the original web site.\nAutomatic renewal will be implemented later.")
        self.location('%s://%s/outil/UWSP/Synthese'
                      % (self.PROTOCOL, self.DOMAIN),
                      no_login=True)

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('https://particuliers.secure.lcl.fr/outil/UWSP/Synthese')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        self.location(account._link_id)
        for tr in self.page.get_operations():
            yield tr

        for tr in self.get_cb_operations(account, 1):
            yield tr

    def get_cb_operations(self, account, month=0):
        """
        Get CB operations.

        * month=0 : current operations (non debited)
        * month=1 : previous month operations (debited)
        """
        for link in account._coming_links:
            v = urlsplit(self.absurl(link))
            args = dict(parse_qsl(v.query))
            args['MOIS'] = month

            self.location(self.buildurl(v.path, **args))

            for tr in self.page.get_operations():
                yield tr

            for card_link in self.page.get_cards():
                self.location(card_link)
                for tr in self.page.get_operations():
                    yield tr

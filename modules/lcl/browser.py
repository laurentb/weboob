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
from mechanize import Cookie

from weboob.deprecated.browser import Browser, BrowserIncorrectPassword

from .pages import SkipPage, LoginPage, AccountsPage, AccountHistoryPage, \
                   CBListPage, CBHistoryPage, ContractsPage


__all__ = ['LCLBrowser','LCLProBrowser']


# Browser
class LCLBrowser(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'particuliers.secure.lcl.fr'
    CERTHASH = ['825a1cda9f3c7176af327013a20145ad587d1f7e2a7e226a1cb5c522e6e00b84']
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
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
            self.location('%s://%s/outil/UWSP/Synthese'
                      % (self.PROTOCOL, self.DOMAIN))

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


class LCLProBrowser(LCLBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'professionnels.secure.lcl.fr'
    CERTHASH = ['6ae7053ef30f7c7810673115b021a42713f518f3a87b2e73ef565c16ead79f81']
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'https://professionnels.secure.lcl.fr/outil/UAUT?from=/outil/UWHO/Accueil/': LoginPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT\?from=.*': LoginPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT/Accueil/preRoutageLogin': LoginPage,
        'https://professionnels.secure.lcl.fr//outil/UAUT/Contract/routing': LoginPage,
        'https://professionnels.secure.lcl.fr/outil/UWER/Accueil/majicER': LoginPage,
        'https://professionnels.secure.lcl.fr/outil/UWER/Enregistrement/forwardAcc': LoginPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT/Contrat/choixContrat.*': ContractsPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT/Contract/getContract.*': ContractsPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT/Contract/selectContracts.*': ContractsPage,
        'https://professionnels.secure.lcl.fr/outil/UWSP/Synthese': AccountsPage,
        'https://professionnels.secure.lcl.fr/outil/UWLM/ListeMouvements.*/accesListeMouvements.*': AccountHistoryPage,
        'https://professionnels.secure.lcl.fr/outil/UWCB/UWCBEncours.*/listeCBCompte.*': CBListPage,
        'https://professionnels.secure.lcl.fr/outil/UWCB/UWCBEncours.*/listeOperations.*': CBHistoryPage,
        'https://professionnels.secure.lcl.fr/outil/UAUT/Contrat/selectionnerContrat.*': SkipPage,
        'https://professionnels.secure.lcl.fr/index.html': SkipPage
        }
    #We need to add this on the login form
    IDENTIFIANT_ROUTING = 'CLA'

    def add_cookie(self, name, value):
        c = Cookie(0, name, value,
                      None, False,
                      '.' + self.DOMAIN, True, True,
                      '/', False,
                      False,
                      None,
                      False,
                      None,
                      None,
                      {})
        cookiejar = self._ua_handlers["_cookies"].cookiejar
        cookiejar.set_cookie(c)

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)
        self.add_cookie("lclgen","professionnels")

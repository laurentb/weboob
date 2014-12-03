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


import urllib
from urlparse import urlsplit, parse_qsl

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login

from .pages import LoginPage, AccountsPage, AccountHistoryPage, \
                   CBListPage, CBHistoryPage, ContractsPage


__all__ = ['LCLBrowser','LCLProBrowser']


# Browser
class LCLBrowser(LoginBrowser):
    BASEURL = 'https://particuliers.secure.lcl.fr'

    login = URL('/outil/UAUT/Authentication/authenticate',
                '/outil/UAUT\?from=.*',
                '/outil/UAUT/Accueil/preRoutageLogin',
                '.*outil/UAUT/Contract/routing',
                '/outil/UWER/Accueil/majicER',
                '/outil/UWER/Enregistrement/forwardAcc',
                LoginPage)
    contracts = URL('/outil/UAUT/Contrat/choixContrat.*',
                    '/outil/UAUT/Contract/getContract.*',
                    '/outil/UAUT/Contract/selectContracts.*',
                    ContractsPage)
    accounts = URL('/outil/UWSP/Synthese', AccountsPage)
    history = URL('/outil/UWLM/ListeMouvements.*/accesListeMouvements.*', AccountHistoryPage)
    cb_list = URL('/outil/UWCB/UWCBEncours.*/listeCBCompte.*', CBListPage)
    cb_history = URL('/outil/UWCB/UWCBEncours.*/listeOperations.*', CBHistoryPage)
    skip = URL('/outil/UAUT/Contrat/selectionnerContrat.*',
               '/index.html')

    def deinit(self):
        pass

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        self.login.stay_or_go()

        if not self.page.login(self.username, self.password) or \
           (self.login.is_here() and self.page.is_error()) :
            raise BrowserIncorrectPassword("invalid login/password.\nIf you did not change anything, be sure to check for password renewal request\non the original web site.\nAutomatic renewal will be implemented later.")

        self.accounts.stay_or_go()

    @need_login
    def get_accounts_list(self):
        self.accounts.stay_or_go()
        return self.page.get_list()

    @need_login
    def get_history(self, account):
        self.location(account._link_id)
        for tr in self.page.get_operations():
            yield tr

        for tr in self.get_cb_operations(account, 1):
            yield tr

    @need_login
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

            self.location('%s?%s' % (v.path, urllib.urlencode(args)))

            for tr in self.page.get_operations():
                yield tr

            for card_link in self.page.get_cards():
                self.location(card_link)
                for tr in self.page.get_operations():
                    yield tr


class LCLProBrowser(LCLBrowser):
    BASEURL = 'https://professionnels.secure.lcl.fr'

    #We need to add this on the login form
    IDENTIFIANT_ROUTING = 'CLA'

    def __init__(self, *args, **kwargs):
        super(LCLProBrowser, self).__init__(*args, **kwargs)
        self.session.cookies.set("lclgen","professionnels")

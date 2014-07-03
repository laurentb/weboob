# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, LoginResultPage, AccountsPage, EmptyPage, TransactionsPage


__all__ = ['BredBrowser']


class BredBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'www.bred.fr'
    CERTHASH = ['9b77dab9c84e1dc9e0798de561a6541ff15f038f60b36ca74c29be1def6c19a3', '375f1fed165d34aacaaf71674ab14ca6c1b38404cf748278714fde3c58385ff0', '0853a056453b56aea6a29085ef3f3721b18db2052aa8e84220720d44e0eb22af']
    ENCODING = 'iso-8859-15'
    PAGES = {r'https://www.\w+.fr/mylittleform.*':                      LoginPage,
             r'https://www.\w+.fr/Andromede/MainAuth.*':                LoginResultPage,
             r'https://www.\w+.fr/Andromede/Main':                      AccountsPage,
             r'https://www.\w+.fr/Andromede/Ecriture':                  TransactionsPage,
             r'https://www.\w+.fr/Andromede/applications/index.jsp':    EmptyPage,
             r'https://www.bred.fr/':                                   EmptyPage,
             r'https://www.dispobank.fr/?':                             LoginPage,
            }

    URLS = {'bred': {'home': 'https://www.bred.fr/Andromede/Main',
                     'login': 'https://www.bred.fr/mylittleform?type=1',
                    },
            'dispobank': {'home': 'https://www.dispobank.fr',
                          'login': 'https://www.dispobank.fr',
                         }
           }

    def __init__(self, website, accnum, *args, **kwargs):
        self.accnum = accnum.replace(' ','').zfill(11)
        self.DOMAIN = 'www.%s.fr' % website
        self.website = website
        BaseBrowser.__init__(self, *args, **kwargs)

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if not self.is_logged():
            self.login()
        else:
            self.location(self.URLS[self.website]['home'])

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location(self.URLS[self.website]['login'], no_login=True)

        self.page.login(self.username, self.password)

        assert self.is_on_page((LoginResultPage, EmptyPage))

        if self.is_on_page(LoginResultPage):
            error = self.page.get_error()
            if error is not None:
                raise BrowserIncorrectPassword(error)

            self.page.confirm()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('https://www.%s.fr/Andromede/Main' % self.website)
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def iter_transactions(self, id, is_coming=None):
        numero_compte, numero_poste = id.split('.')
        data = {'typeDemande':      'recherche',
                'motRecherche':     '',
                'numero_compte':    numero_compte,
                'numero_poste':     numero_poste,
                'detail':           '',
                'tri':              'date',
                'sens':             'sort',
                'monnaie':          'EUR',
                'index_hist':       4
               }
        self.location('https://www.%s.fr/Andromede/Ecriture' % self.website, urllib.urlencode(data))

        assert self.is_on_page(TransactionsPage)
        return self.page.get_history(is_coming)

    def get_history(self, account):
        for tr in self.iter_transactions(account.id):
            yield tr

        for tr in self.get_card_operations(account):
            yield tr

    def get_card_operations(self, account):
        for id in account._card_links:
            for tr in self.iter_transactions(id, True):
                yield tr

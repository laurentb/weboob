# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import LoginBrowser, need_login, URL
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, LoginResultPage, AccountsPage, EmptyPage, TransactionsPage


__all__ = ['DispoBankBrowser']


class DispoBankBrowser(LoginBrowser):
    BASEURL = 'https://www.dispobank.fr'
    login_page = URL(r'https://www.\w+.fr/mylittleform.*', LoginPage)
    login_result = URL(r'https://www.\w+.fr/Andromede/MainAuth.*', LoginResultPage)
    accounts_page = URL(r'https://www.\w+.fr/Andromede/Main', AccountsPage)
    transactions_page = URL(r'https://www.\w+.fr/Andromede/Ecriture', TransactionsPage)
    empty_page = URL(r'https://www.\w+.fr/Andromede/applications/index.jsp',
                     r'https://www.bred.fr/',
                     EmptyPage)
    login2 = URL(r'https://www.dispobank.fr/?', LoginPage)

    URLS = {'bred': {'home': 'https://www.bred.fr/Andromede/Main',
                     'login': 'https://www.bred.fr/mylittleform?type=1',
                    },
            'dispobank': {'home': 'https://www.dispobank.fr',
                          'login': 'https://www.dispobank.fr',
                         }
           }

    def __init__(self, accnum, *args, **kwargs):
        super(DispoBankBrowser, self).__init__(*args, **kwargs)
        self.accnum = accnum
        self.website = 'dispobank'

    def home(self):
        self.location(self.URLS[self.website]['home'])

    def do_login(self):
        if not (self.login_page.is_here() or self.login2.is_here()):
            self.location(self.URLS[self.website]['login'])

        self.page.login(self.username, self.password)

        assert self.login_result.is_here() or self.empty_page.is_here()

        if self.login_result.is_here():
            error = self.page.get_error()
            if error is not None:
                raise BrowserIncorrectPassword(error)

            self.page.confirm()

    @need_login
    def get_accounts_list(self):
        if not self.accounts_page.is_here():
            self.location('https://www.%s.fr/Andromede/Main' % self.website)
        return self.page.get_list()

    @need_login
    def get_history(self, account, coming=False):
        if coming:
            raise NotImplementedError()

        numero_compte, numero_poste = account.id.split('.')
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
        self.location('https://www.%s.fr/Andromede/Ecriture' % self.website, data=data)

        assert self.transactions_page.is_here()
        return self.page.get_history()

    def get_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        if not self.accounts_page.is_here():
            self.location('https://www.%s.fr/Andromede/Main' % self.website)

        return self.page.get_profile()

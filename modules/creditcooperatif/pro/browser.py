# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from .pages import LoginPage, AccountsPage, ITransactionsPage, TransactionsPage, ComingTransactionsPage, CardTransactionsPage


__all__ = ['CreditCooperatif']


class CreditCooperatif(Browser):
    PROTOCOL = 'https'
    ENCODING = 'iso-8859-15'
    DOMAIN = "www.coopanet.com"
    PAGES = {'https://www.coopanet.com/banque/sso/.*': LoginPage,
             'https://www.coopanet.com/banque/cpt/incoopanetj2ee.do.*': AccountsPage,
             'https://www.coopanet.com/banque/cpt/cpt/situationcomptes.do\?lnkReleveAction=X&numeroExterne=.*': TransactionsPage,
             'https://www.coopanet.com/banque/cpt/cpt/relevecompte.do\?tri_page=.*': TransactionsPage,
             'https://www.coopanet.com/banque/cpt/cpt/situationcomptes.do\?lnkOpCB=X&numeroExterne=.*': CardTransactionsPage,
             'https://www.coopanet.com/banque/cpt/cpt/situationcomptes.do\?lnkOpEC=X&numeroExterne=.*': ComingTransactionsPage,
             'https://www.coopanet.com/banque/cpt/cpt/operationEnCours.do.*': ComingTransactionsPage,
            }

    def __init__(self, *args, **kwargs):
        self.strong_auth = kwargs.pop('strong_auth', False)
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location("/banque/sso/")

        assert self.is_on_page(LoginPage)

    def is_logged(self):
        return not self.is_on_page(LoginPage)

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """

        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert isinstance(self.strong_auth, bool)

        if self.is_logged():
            return

        if not self.is_on_page(LoginPage):
            self.home()

        self.page.login(self.username, self.password, self.strong_auth)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        self.location(self.buildurl('/banque/cpt/incoopanetj2ee.do?ssomode=ok'))

        return self.page.get_list()

    def _get_history(self, link):
        self.location(link)

        while True:
            assert self.is_on_page(ITransactionsPage)

            for tr in self.page.get_history():
                yield tr

            next_url = self.page.get_next_url()
            if next_url is None:
                return

            self.location(next_url)

    def get_history(self, account):
        return self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkReleveAction=X&numeroExterne='+ account.id)

    def get_coming(self, account):
        # credit cards transactions
        for tr in self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkOpCB=X&numeroExterne='+ account.id):
            yield tr
        # coming transactions
        for tr in self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkOpEC=X&numeroExterne='+ account.id):
            yield tr

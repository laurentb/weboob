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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.compat import urljoin

from .pages import LoginPage, AccountsPage, ITransactionsPage, TransactionsPage, ComingTransactionsPage, CardTransactionsPage, \
                   TechnicalErrorPage, ProfilePage


__all__ = ['CreditCooperatif']


class CreditCooperatif(LoginBrowser):
    login_page = URL(r'https?://[^/]+/banque/sso/.*', LoginPage)
    accounts = URL(r'https?://[^/]+/banque/cpt/incoopanetj2ee.do.*', AccountsPage)
    transactions = URL(r'https?://[^/]+/banque/cpt/cpt/situationcomptes.do\?lnkReleveAction=X&numeroExterne=.*',
                       r'https?://[^/]+/banque/cpt/cpt/relevecompte.do\?tri_page=.*',
                       TransactionsPage)
    card_transactions = URL(r'https?://[^/]+/banque/cpt/cpt/situationcomptes.do\?lnkOpCB=X&numeroExterne=.*',
                            r'https?://[^/]+/banque/cpt/cpt/operationscartebancaire.do\?.*',
                            r'https://[^/]+/banque/cpt/cpt/encourscartesbancaires.do\?index=.*',
                            CardTransactionsPage)
    comings = URL(r'https?://[^/]+/banque/cpt/cpt/situationcomptes.do\?lnkOpEC=X&numeroExterne=.*',
                  r'https?://[^/]+/banque/cpt/cpt/operationEnCours.do.*',
                  ComingTransactionsPage)
    error = URL(r'https?://[^/]+/PbTechniqueCoopanet.htm', TechnicalErrorPage)
    profile = URL(r'https?://[^/]+/banque/cdc/incoopanetj2ee.do\?ssomode=true&idMenu=48&idParent=13',
                  r'https?://[^/]+/banque/cpt/cpt/menucptaction.do\?idMenu=48&idParent=13', ProfilePage)

    def __init__(self, baseurl, *args, **kwargs):
        self.BASEURL = baseurl
        self.strong_auth = kwargs.pop('strong_auth', False)
        super(CreditCooperatif, self).__init__(*args, **kwargs)

    @need_login
    def get_profile(self):
        self.location(urljoin(self.url, r'/banque/cpt/cpt/menucptaction.do?idMenu=48&idParent=13'))
        self.location(urljoin(self.url ,r'/banque/cdc/incoopanetj2ee.do?ssomode=true&idMenu=48&idParent=13'))
        return self.page.get_profile()

    def home(self):
        self.location("/banque/sso/")
        if self.error.is_here():
            raise BrowserUnavailable()
        assert self.login_page.is_here()

    def do_login(self):
        assert isinstance(self.strong_auth, bool)

        if not self.login_page.is_here():
            self.home()

        self.page.login(self.username, self.password, self.strong_auth)

        if not self.page or self.login_page.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_accounts_list(self):
        self.location(self.absurl('/banque/cpt/incoopanetj2ee.do?ssomode=ok'))
        return self.page.get_list()

    @need_login
    def _get_history(self, link):
        self.location(link)

        while True:
            assert isinstance(self.page, ITransactionsPage)

            for tr in self.page.get_history():
                yield tr

            next_url = self.page.get_next_url()
            if next_url is None:
                return

            self.location(next_url)

    @need_login
    def get_history(self, account):
        return self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkReleveAction=X&numeroExterne='+ account.id)

    @need_login
    def get_coming(self, account):
        # credit cards transactions
        for tr in self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkOpCB=X&numeroExterne='+ account.id):
            yield tr
        # coming transactions
        for tr in self._get_history('/banque/cpt/cpt/situationcomptes.do?lnkOpEC=X&numeroExterne='+ account.id):
            yield tr

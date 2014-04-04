# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014      Romain Bignon
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

from .pages import LoginPage, IndexPage, AccountsPage, OperationsPage


__all__ = ['BanqueAccordBrowser']


class BanqueAccordBrowser(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'www.banque-accord.fr'
    ENCODING = None

    PAGES = {
        'https://www.banque-accord.fr/site/s/login/login.html':                             LoginPage,
        'https://www.banque-accord.fr/site/s/detailcompte/detailcompte.html':               IndexPage,
        'https://www.banque-accord.fr/site/s/detailcompte/ongletdetailcompte.html':         AccountsPage,
        'https://www.banque-accord.fr/site/s/detailcompte/ongletdernieresoperations.html':  OperationsPage,
    }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if self.is_logged():
            self.location('/site/s/detailcompte/detailcompte.html')
        else:
            self.login()

    def login(self):
        """
        Attempt to log in.
        Note: this method does nothing if we are already logged in.
        """
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if self.is_logged():
            return

        self.location('/site/s/login/login.html', no_login=True)
        assert self.is_on_page(LoginPage)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(IndexPage):
             self.location('https://www.banque-accord.fr/site/s/detailcompte/detailcompte.html')

        for a in self.page.get_list():
            post = {'numeroCompte': a.id,}
            self.location('/site/s/detailcompte/detailcompte.html', urllib.urlencode(post))

            a.balance = self.page.get_loan_balance()
            if a.balance is not None:
                a.type = a.TYPE_LOAN
            else:
                self.location('/site/s/detailcompte/ongletdetailcompte.html')
                a.balance = self.page.get_balance()
                a.type = a.TYPE_CARD
            yield a

    def get_account(self, id):
        assert isinstance(id, basestring)
        if not self.is_on_page(IndexPage):
            self.home()

        for a in self.get_accounts_list():
            if a.id == id:
                return a
        return None

    def iter_history(self, account):
        if account.type != account.TYPE_CARD:
            return iter([])

        post = {'numeroCompte': account.id}
        self.location('/site/s/detailcompte/detailcompte.html', urllib.urlencode(post))
        self.location('/site/s/detailcompte/ongletdernieresoperations.html')

        assert self.is_on_page(OperationsPage)
        return self.page.get_history()

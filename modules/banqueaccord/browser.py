# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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
from weboob.capabilities.bank import Account

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


    def get_account(self):
        if not self.is_on_page(IndexPage):
            self.home()

        account = Account()
        account.id = '0'
        account.label = self.page.get_card_name()

        self.location('/site/s/detailcompte/ongletdetailcompte.html')
        account.balance = self.page.get_balance()

        return account

    def iter_history(self, account):
        self.location('/site/s/detailcompte/ongletdernieresoperations.html')

        assert self.is_on_page(OperationsPage)
        return self.page.get_history()

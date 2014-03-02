# -*- coding: utf-8 -*-

# Copyright(C) 2014 Romain Bignon
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

from .pages import LoginPage, AccountsPage


__all__ = ['AlloRestoBrowser']


class AlloRestoBrowser(BaseBrowser):
    DOMAIN = 'www.alloresto.fr'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    PAGES = {'http://www.alloresto.fr/identification-requise.*':         LoginPage,
             'http://www.alloresto.fr/chez-moi/releve-compte-miams':    AccountsPage,
            }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        self.go_on_accounts_list()

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.is_on_page(LoginPage):
            self.location('http://www.alloresto.fr/identification-requise', no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def go_on_accounts_list(self):
        self.location('http://www.alloresto.fr/chez-moi/releve-compte-miams')

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.go_on_accounts_list()
        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        l = self.get_accounts_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if not self.is_on_page(AccountsPage):
            self.go_on_accounts_list()

        return self.page.get_transactions()

    def get_coming(self, account):
        if not self.is_on_page(AccountsPage):
            self.go_on_accounts_list()

        return self.page.get_transactions('acquisition')

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


from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage, TransactionsPage


__all__ = ['Cmso']


class Cmso(BaseBrowser):
    PROTOCOL = 'https'
    DOMAIN = 'www.cmso.com'
    ENCODING = 'iso-8859-1'
    PAGES = {'https://www.cmso.com/domimobile/m.jsp\?a=signin.*':       LoginPage,
             'https://www.cmso.com/domimobile/m.jsp\?a=sommaire.*':     AccountsPage,
             'https://www.cmso.com/domimobile/m.jsp\?a=solde.*':        TransactionsPage,
             'https://www.cmso.com/domimobile/m.jsp\?rels=.*':          TransactionsPage,
            }

    def is_logged(self):
        return self.page is not None and not self.is_on_page(LoginPage)

    def home(self):
        if self.is_logged():
            self.location('https://www.cmso.com/domimobile/m.jsp?a=sommaire')
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

        if not self.is_on_page(LoginPage):
            self.location('https://www.cmso.com/domimobile/m.jsp?a=signin&b=sommaire', no_login=True)

        self.page.login(self.username, self.password)

        if not self.is_logged():
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(AccountsPage):
            self.location('https://www.cmso.com/domimobile/m.jsp?a=sommaire')
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
            self.location('https://www.cmso.com/domimobile/m.jsp?a=sommaire')

        link = account._link

        while link is not None:
            self.location(link)
            assert self.is_on_page(TransactionsPage)

            for tr in self.page.get_history():
                yield tr

            link = self.page.get_next_link()

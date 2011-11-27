# -*- coding: utf-8 -*-

# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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
from weboob.backends.boursorama import pages


__all__ = ['boursorama']


class Boursorama(BaseBrowser):
    DOMAIN = 'www.boursorama.com'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
             '.*connexion.phtml.*':  pages.LoginPage,
             '.*/comptes/synthese.phtml':      pages.AccountsList,
             '.*/comptes/banque/detail/mouvements.phtml.*': pages.AccountHistory,
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://' + self.DOMAIN + '/connexion.phtml')

    def is_logged(self):
        return not self.is_on_page(pages.LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(pages.LoginPage):
            self.location('https://' + self.DOMAIN + '/connexion.phtml')

        self.page.login(self.username, self.password)

        if self.is_on_page(pages.LoginPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList):
            self.location('/comptes/synthese.phtml')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(pages.AccountsList):
            self.location('/comptes/synthese.phtml')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        if not self.is_on_page(pages.AccountHistory) or self.page.account.id != account.id:
            self.location(account.link_id)
        return self.page.get_operations()

    def transfer(self, from_id, to_id, amount, reason=None):
        raise NotImplementedError()

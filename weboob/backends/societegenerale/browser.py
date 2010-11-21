# -*- coding: utf-8 -*-

# Copyright(C) 2010  Jocelyn Jaubert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from datetime import datetime
from logging import warning

from weboob.tools.browser import BaseBrowser, BrowserIncorrectPassword
from weboob.capabilities.bank import TransferError, Transfer
from weboob.backends.societegenerale import pages


__all__ = ['SocieteGenerale']


class SocieteGenerale(BaseBrowser):
    DOMAIN_LOGIN = 'particuliers.societegenerale.fr'
    DOMAIN = 'particuliers.secure.societegenerale.fr'
    PROTOCOL = 'https'
    ENCODING = None # refer to the HTML encoding
    PAGES = {
             'https://particuliers.societegenerale.fr/.*':  pages.LoginPage,
             '.*restitution/cns_listeprestation.html':      pages.AccountsList,
#             '.*restitution/cns_detailCav.html.*':          pages.AccountHistory,
            }

    def __init__(self, *args, **kwargs):
        BaseBrowser.__init__(self, *args, **kwargs)

    def home(self):
        self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

    def is_logged(self):
        return not self.is_on_page(pages.LoginPage)

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.password.isdigit()

        if not self.is_on_page(pages.LoginPage):
            self.location('https://' + self.DOMAIN_LOGIN + '/index.html')

        self.page.login(self.username, self.password)

        if self.is_on_page(pages.LoginPage):
            raise BrowserIncorrectPassword()

    def get_accounts_list(self):
        if not self.is_on_page(pages.AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        return self.page.get_list()

    def get_account(self, id):
        assert isinstance(id, basestring)

        if not self.is_on_page(pages.AccountsList):
            self.location('/restitution/cns_listeprestation.html')

        l = self.page.get_list()
        for a in l:
            if a.id == id:
                return a

        return None

    def get_history(self, account):
        raise NotImplementedError()

        if not self.is_on_page(pages.AccountHistory) or self.page.account.id != account.id:
            self.location(account.link_id)
        return self.page.get_operations()

    def transfer(self, from_id, to_id, amount, reason=None):
        raise NotImplementedError()

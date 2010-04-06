# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backend import Backend
from weboob.capabilities.bank import ICapBank, AccountNotFound

from .browser import BNPorc

class BNPorcBackend(Backend, ICapBank):
    NAME = 'bnporc'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '1.0'
    LICENSE = 'GPLv3'
    DESCRIPTION = 'BNP Paribas french bank\' website'

    CONFIG = {'login':    Backend.ConfigField(description='Account ID'),
              'password': Backend.ConfigField(description='Password of account', is_masked=True)
             }
    browser = None

    def need_browser(func):
        def inner(self, *args, **kwargs):
            if not self.browser:
                self.browser = BNPorc(self.config['login'], self.config['password'])

            return func(self, *args, **kwargs)
        return inner

    @need_browser
    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    @need_browser
    def get_account(self, _id):
        try:
            _id = long(_id)
        except ValueError:
            raise AccountNotFound()
        else:
            account = self.browser.get_account(_id)
            if account:
                return account
            else:
                raise AccountNotFound()

    @need_browser
    def iter_operations(self, account):
        for coming in self.browser.get_coming_operations(account):
            yield coming

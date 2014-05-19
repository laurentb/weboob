# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import ICapBank, AccountNotFound

from .browser import CitelisBrowser


__all__ = ['CitelisBackend']


class CitelisBackend(BaseBackend, ICapBank):
    NAME = 'citelis'
    DESCRIPTION = u'Citélis'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'

    BROWSER = CitelisBrowser

    CONFIG = BackendConfig(
        ValueBackendPassword('merchant_id', label='Merchant ID', masked=False),
        ValueBackendPassword('login', label='Account ID', masked=False),
        ValueBackendPassword('password', label='Password'))

    def create_default_browser(self):
        return self.create_browser(self.config['merchant_id'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        for account in self.iter_accounts():
            if account.id == _id:
                return account
        raise AccountNotFound()

    def iter_history(self, account):
        return self.browser.iter_history(account)

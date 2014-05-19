# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013  Romain Bignon, Pierre Mazière
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




from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import LCLBrowser
from .enterprise.browser import LCLEnterpriseBrowser


__all__ = ['LCLBackend']


class LCLBackend(BaseBackend, ICapBank):
    NAME = 'lcl'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = u'LCL'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code personnel'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers',
                                          'ent': 'Entreprises'}))
    BROWSER = LCLBrowser

    def create_default_browser(self):
        website = self.config['website'].get()
        if website == 'ent':
            self.BROWSER = LCLEnterpriseBrowser
            return self.create_browser(self.config['login'].get(),
                                       self.config['password'].get())
        else:
            self.BROWSER = LCLBrowser
            return self.create_browser(self.config['login'].get(),
                                       self.config['password'].get())

    def deinit(self):
        # don't need to logout if the browser hasn't been used.
        if not self._browser:
            return

        try:
            deinit = self.browser.deinit
        except AttributeError:
            pass
        else:
            deinit()

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_coming(self, account):
        if self.BROWSER != LCLBrowser:
            raise NotImplementedError

        with self.browser:
            transactions = list(self.browser.get_cb_operations(account))
            transactions.sort(key=lambda tr: tr.rdate, reverse=True)
            return transactions

    def iter_history(self, account):
        with self.browser:
            transactions = list(self.browser.get_history(account))
            transactions.sort(key=lambda tr: tr.rdate, reverse=True)
            return transactions

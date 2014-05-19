# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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

from .browser import BredBrowser


__all__ = ['BredBackend']


class BredBackend(BaseBackend, ICapBank):
    NAME = 'bred'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.j'
    DESCRIPTION = u'Bred'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'),
                           Value('website', label="Site d'accès", default='bred',
                                 choices={'bred': 'BRED', 'dispobank': 'DispoBank'}),
                           Value('accnum', label='Account number to force (optional)', default='', masked=False)
                          )
    BROWSER = BredBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get(),
                                   self.config['accnum'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        with self.browser:
            for account in self.browser.get_accounts_list():
                yield account

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)

        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        with self.browser:
            transactions = list(self.browser.get_history(account))
            transactions.sort(key=lambda tr: tr.rdate, reverse=True)
            return [tr for tr in transactions if not tr._is_coming]

    def iter_coming(self, account):
        with self.browser:
            transactions = list(self.browser.get_card_operations(account))
            transactions.sort(key=lambda tr: tr.rdate, reverse=True)
            return [tr for tr in transactions if tr._is_coming]

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals


from weboob.capabilities.bank import CapBank, Account, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import MyedenredBrowser


__all__ = ['MyedenredModule']


class MyedenredModule(Module, CapBank):
    NAME = 'myedenred'
    DESCRIPTION = 'MyEdenRed'
    MAINTAINER = 'Théo Dorée'
    EMAIL = 'tdoree@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Adresse email', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))

    BROWSER = MyedenredBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, id):
        return find_object(self.iter_accounts(), id=id, error=AccountNotFound)

    def iter_history(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.iter_history(account)

# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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

from weboob.capabilities.bank import CapBankWealth
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import ApivieBrowser


__all__ = ['ApivieModule']


class ApivieModule(Module, CapBankWealth):
    NAME = 'apivie'
    DESCRIPTION = u'Apivie'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'

    BROWSER = ApivieBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))

    def create_default_browser(self):
        return self.create_browser('www.apivie.fr',
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def get_account(self, _id):
        return self.browser.get_account(_id)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_history(self, account):
        return self.browser.iter_history(account)

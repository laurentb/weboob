# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.base import find_object

from .browser import DegiroBrowser


__all__ = ['DegiroModule']


class DegiroModule(Module, CapBankWealth):
    NAME = 'degiro'
    DESCRIPTION = u'De giro'
    MAINTAINER = u'Jean Walrave'
    EMAIL = 'jwalrave@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Nom d\'utilisateur', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))

    BROWSER = DegiroBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

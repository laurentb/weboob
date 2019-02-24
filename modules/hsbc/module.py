# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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


from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.profile import CapProfile
from .browser import HSBC


__all__ = ['HSBCModule']


class HSBCModule(Module, CapBankWealth, CapProfile):
    NAME = 'hsbc'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'HSBC France'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Mot de passe'),
                           ValueBackendPassword('secret',     label=u'Réponse secrète'))
    BROWSER = HSBC

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get(),
                                   self.config['secret'].get())

    def iter_accounts(self):
        for account in self.browser.iter_account_owners():
            yield account

    def get_account(self, _id):
        return find_object(self.browser.iter_account_owners(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        for tr in self.browser.get_history(account):
            yield tr

    def iter_investment(self, account):
        for tr in self.browser.get_investments(account):
            yield tr

    def iter_coming(self, account):
        for tr in self.browser.get_history(account, coming=True):
            yield tr

    def get_profile(self):
        return self.browser.get_profile()

# -*- coding: utf-8 -*-

# Copyright(C) 2014 Budget Insight
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


from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import OneyBrowser


__all__ = ['OneyModule']


class OneyModule(Module, CapBank):
    NAME = 'oney'
    MAINTAINER = u'Vincent Paredes'
    EMAIL = 'vparedes@budget-insight.com'
    VERSION = '1.3'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'Oney'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Mot de passe'))
    BROWSER = OneyBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        # To prevent issues in calcul of actual balance and coming one, all
        # operations are marked as debited.
        for tr in self.browser.iter_coming(account):
            yield tr

        for tr in self.browser.iter_history(account):
            yield tr

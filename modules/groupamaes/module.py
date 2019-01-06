# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from weboob.capabilities.bank import CapBankPockets, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.base import find_object

from .browser import GroupamaesBrowser


__all__ = ['GroupamaesModule']


class GroupamaesModule(Module, CapBankPockets):
    NAME = 'groupamaes'
    DESCRIPTION = u"Groupama Épargne Salariale"
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = GroupamaesBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login', label='Identifiant', regexp='\d{8,}', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def iter_coming(self, account):
        return self.browser.get_coming()

    def iter_history(self, account):
        return self.browser.get_history()

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_pocket(self, account):
        return self.browser.iter_pocket(account)

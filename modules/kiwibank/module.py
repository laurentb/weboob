# -*- coding: utf-8 -*-

# Copyright(C) 2015 Cédric Félizard
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


from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import Kiwibank


__all__ = ['KiwibankModule']


class KiwibankModule(Module, CapBank):
    NAME = 'kiwibank'
    MAINTAINER = u'Cédric Félizard'
    EMAIL = 'cedric@felizard.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Kiwibank'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Access number', masked=False),
        ValueBackendPassword('password', label='Password'),
    )
    BROWSER = Kiwibank

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        for transaction in self.browser.get_history(account):
            yield transaction

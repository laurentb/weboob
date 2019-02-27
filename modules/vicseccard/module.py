# -*- coding: utf-8 -*-

# Copyright(C) 2015      Oleg Plakhotniuk
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

from weboob.capabilities.bank import CapBank
from weboob.tools.backend import BackendConfig, Module
from weboob.tools.value import ValueBackendPassword

from .browser import VicSecCard

__all__ = ['VicSecCardModule']


class VicSecCardModule(Module, CapBank):
    NAME = 'vicseccard'
    MAINTAINER = u'Oleg Plakhotniuk'
    EMAIL = 'olegus8@gmail.com'
    VERSION = '1.6'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Victoria\'s Secret Angel Card'
    CONFIG = BackendConfig(
        ValueBackendPassword('username', label='User name', masked=False),
        ValueBackendPassword('password', label='Password'))
    BROWSER = VicSecCard

    def create_default_browser(self):
        return self.create_browser(self.config['username'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def get_account(self, id_):
        return self.browser.get_account(id_)

    def iter_history(self, account):
        return self.browser.iter_history(account)

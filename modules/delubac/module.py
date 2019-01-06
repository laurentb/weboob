# -*- coding: utf-8 -*-

# Copyright(C) 2013      Noe Rubinstein
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

from weboob.capabilities.bank import CapBank
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import DelubacBrowser


__all__ = ['DelubacModule']


class DelubacModule(Module, CapBank, CapProfile):
    NAME = 'delubac'
    DESCRIPTION = u'Banque Delubac & Cie'
    MAINTAINER = u'Noe Rubinstein'
    EMAIL = 'nru@budget-insight.com'
    VERSION = '1.5'

    BROWSER = DelubacBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe', regexp='^\d+$'))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def get_account(self, _id):
        return self.browser.get_account(_id)

    def iter_history(self, account, coming=False):
        return self.browser.iter_history(account)

    def get_profile(self):
        return self.browser.get_profile()

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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


#from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import HSBCHK


__all__ = ['HSBCHKModule']


class HSBCHKModule(Module, CapBank):
    NAME = 'hsbchk'
    MAINTAINER = u'sinopsysHK'
    EMAIL = 'sinofwd@gmail.com'
    VERSION = '1.6'
    LICENSE = 'LGPLv3+'
    DESCRIPTION = 'HSBC Hong Kong'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='User identifier', masked=False),
                           ValueBackendPassword('password',   label='Password'),
                           ValueBackendPassword('secret',     label=u'Memorable answer'))
    BROWSER = HSBCHK

    def create_default_browser(self):
        return self.create_browser(
            self.config['login'].get(),
            self.config['password'].get(),
            self.config['secret'].get()
        )

    def iter_accounts(self):
        for account in self.browser.iter_accounts():
            yield account

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        for tr in self.browser.get_history(account):
            yield tr

    def iter_investment(self, account):
        raise NotImplementedError

    def iter_coming(self, account):
        # No coming entries on HSBC HK
        return []

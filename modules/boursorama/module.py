# -*- coding: utf-8 -*-

# Copyright(C) 2012      Gabriel Serme
# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, ValueBool, Value

from .browser import Boursorama


__all__ = ['BoursoramaModule']


class BoursoramaModule(Module, CapBank):
    NAME = 'boursorama'
    MAINTAINER = u'Gabriel Kerneis'
    EMAIL = 'gabriel@kerneis.info'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Boursorama'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Mot de passe'),
                           ValueBool('enable_twofactors',     label='Send validation sms', default=False),
                           Value('device',                    label='Device name', regexp='\w*', default=''),
                           Value('pin_code',                  label='Sms code', required=False),
                          )
    BROWSER = Boursorama

    def create_default_browser(self):
        return self.create_browser(self.config)

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

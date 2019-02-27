# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Romain Bignon
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
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .bred import BredBrowser
from .dispobank import DispoBankBrowser


__all__ = ['BredModule']


class BredModule(Module, CapBankWealth, CapProfile):
    NAME = 'bred'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.6'
    DESCRIPTION = u'Bred'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'),
                           Value('website', label=u"Site d'accès", default='bred',
                                 choices={'bred': 'BRED', 'dispobank': 'DispoBank'}),
                           Value('accnum', label=u'Numéro du compte bancaire (optionnel)', default='', masked=False)
                          )

    BROWSERS = {'bred': BredBrowser,
                'dispobank': DispoBankBrowser,
               }

    def create_default_browser(self):
        self.BROWSER = self.BROWSERS[self.config['website'].get()]

        return self.create_browser(self.config['accnum'].get().replace(' ','').zfill(11),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_history(account, coming=True)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def get_profile(self):
        return self.browser.get_profile()

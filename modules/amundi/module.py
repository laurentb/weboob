# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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
from weboob.tools.value import ValueBackendPassword, Value

from .browser import EEAmundi, TCAmundi

__all__ = ['AmundiModule']


class AmundiModule(Module, CapBankWealth):
    NAME = 'amundi'
    DESCRIPTION = u'Amundi'
    MAINTAINER = u'James GALT'
    EMAIL = 'james.galt.bi@gmail.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', regexp=r'\d+', masked=False),
                           ValueBackendPassword('password', label=u"Mot de passe", regexp=r'\d+'),
                           Value('website', label='Type de compte', default='ee',
                                 choices={'ee': 'Amundi Epargne Entreprise',
                                          'tc': 'Amundi Tenue de Compte'}))

    def create_default_browser(self):
        b = {'ee': EEAmundi, 'tc': TCAmundi}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def get_account(self, id):
        return find_object(self.iter_accounts(), id=id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_investment(self, account):
        for inv in self.browser.iter_investment(account):
            if inv.valuation != 0:
                yield inv

    def iter_history(self, account):
        return self.browser.iter_history(account)

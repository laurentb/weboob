# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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


from weboob.capabilities.bank import CapBankPockets
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import EEAmundi, TCAmundi

__all__ = ['AmundiModule']


class AmundiModule(Module, CapBankPockets):
    NAME = 'amundi'
    DESCRIPTION = u'Amundi'
    MAINTAINER = u'James GALT'
    EMAIL = 'james.galt.bi@gmail.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', regexp=r'\d+', masked=False),
        ValueBackendPassword('password', label='Mot de passe'),
        Value(
            'website',
            label='Type de compte',
            default='ee',
            choices={
                'ee': 'Amundi Epargne Entreprise',
                'tc': 'Amundi Tenue de Compte'
            }
        )
    )

    def create_default_browser(self):
        b = {'ee': EEAmundi, 'tc': TCAmundi}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_investment(self, account):
        for inv in self.browser.iter_investment(account):
            if inv.valuation != 0:
                yield inv

    def iter_pocket(self, account):
        return self.browser.iter_pockets(account)

    def iter_history(self, account):
        return self.browser.iter_history(account)

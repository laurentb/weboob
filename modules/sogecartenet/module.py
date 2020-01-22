# -*- coding: utf-8 -*-

# Copyright(C) 2015 Budget Insight
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

from __future__ import unicode_literals

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.bank import CapBank
from weboob.tools.value import ValueBackendPassword, Value

from .browser import SogecarteTitulaireBrowser
from .ent_browser import SogecarteEntrepriseBrowser

__all__ = ['SogecartenetModule']


class SogecartenetModule(Module, CapBank):
    NAME = 'sogecartenet'
    DESCRIPTION = 'Sogecarte Net'
    MAINTAINER = 'Guillaume Risbourg'
    EMAIL = 'guillaume.risbourg@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', masked=False),
        ValueBackendPassword('password', label='Mot de passe'),
        Value('website', label="Type d'accès", default='titulaire', choices={
            'titulaire': 'Accès Titulaire de carte Affaires',
            'entreprise': 'Accès Administrateur Entreprise',
        }),
    )

    def create_default_browser(self):
        browsers = {
            'titulaire': SogecarteTitulaireBrowser,
            'entreprise': SogecarteEntrepriseBrowser,
        }
        self.BROWSER = browsers[self.config['website'].get()]
        return self.create_browser(self.config)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_transactions(account)

    def iter_coming(self, account):
        return self.browser.iter_transactions(account, True)

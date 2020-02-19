# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankWealth

from .browser import HumanisBrowser


__all__ = ['HumanisModule']


class HumanisModule(Module, CapBankWealth):
    NAME = 'humanis'
    DESCRIPTION = 'Humanis Épargne Salariale'
    MAINTAINER = 'Quentin Defenouillère'
    EMAIL = 'quentin.defenouillere@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Code d\'accès', masked=False),
        ValueBackendPassword('password', label='Mot de passe')
    )

    BROWSER = HumanisBrowser

    def create_default_browser(self):
        return self.create_browser(
            self.config['login'].get(),
            self.config['password'].get(),
            'https://www.gestion-epargne-salariale.fr',
            'epsens/',
            weboob=self.weboob
        )

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_pocket(self, account):
        return self.browser.iter_pocket(account)

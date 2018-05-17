# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankPockets, AccountNotFound
from weboob.capabilities.base import find_object

from .browser import HumanisBrowser


__all__ = ['HumanisModule']


class HumanisModule(Module, CapBankPockets):
    NAME = 'humanis'
    DESCRIPTION = u'Humanis Épargne Salariale'
    MAINTAINER = u'Jean Walrave'
    EMAIL = 'jwalrave@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.3'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label=u'Code d\'accès', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))

    BROWSER = HumanisBrowser

    def create_default_browser(self):
        return self.create_browser(
            'https://www.gestion-epargne-salariale.fr',
            'humanis/',
            self.config['login'].get(),
            self.config['password'].get(),
            weboob=self.weboob
        )

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_pocket(self, account):
        return self.browser.iter_pocket(account)

# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.bank import CapBankWealth
from weboob.capabilities.profile import CapProfile
from .browser import BnppereBrowser, VisiogoBrowser


__all__ = ['BnppereModule']


class BnppereModule(AbstractModule, CapBankWealth, CapProfile):
    NAME = 'bnppere'
    DESCRIPTION = u'BNP Épargne Salariale'
    MAINTAINER = u'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(
             ValueBackendPassword('login',    label='Identifiant', masked=False),
             ValueBackendPassword('password', label='Code secret'),
             Value('otp', label=u'Code de sécurité', default='', regexp='^(\d{6})$'),
             Value('website', label='Espace Client', default='personeo',
                   choices={'personeo': 'PEE, PERCO (Personeo)', 'visiogo': 'PER Entreprises (Visiogo)'}))
    PARENT = 's2e'

    def create_default_browser(self):
        b = {'personeo': BnppereBrowser, 'visiogo': VisiogoBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config, weboob=self.weboob)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def get_profile(self):
        return self.browser.get_profile()

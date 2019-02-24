# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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


from weboob.capabilities.base import find_object
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import CarrefourBanqueBrowser


__all__ = ['CarrefourBanqueModule']


class CarrefourBanqueModule(Module, CapBankWealth):
    NAME = 'carrefourbanque'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = u'Carrefour Banque'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label=u'Votre Identifiant Internet', masked=False),
                           ValueBackendPassword('password', label=u"Code d'accès",    regexp=u'\d+'),
                           Value('captcha_response', label='Captcha Response', default='', required=False))
    BROWSER = CarrefourBanqueBrowser

    def create_default_browser(self):
        return self.create_browser(self.config)

    def iter_accounts(self):
        return self.browser.get_account_list()

    def get_account(self, _id):
        return find_object(self.browser.get_account_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

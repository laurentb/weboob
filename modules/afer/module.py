# -*- coding: utf-8 -*-

# Copyright(C) 2015      James GALT
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

from weboob.capabilities.base import find_object
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import AferBrowser


__all__ = ['AferModule']


class AferModule(Module, CapBankWealth):
    NAME = 'afer'
    DESCRIPTION = u'Association française d\'épargne et de retraite'
    MAINTAINER = u'James GALT'
    EMAIL = 'jgalt@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'

    BROWSER = AferBrowser
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', regexp=r'.+', masked=False),
        ValueBackendPassword('password', label="Mot de passe", regexp=r'\d{1,8}|[a-zA-Z0-9]{7,30}')
        # TODO lose previous regex (and in backend) once users credentials migration is complete
    )

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())


    def get_account(self, id):
        return find_object(self.iter_accounts(), id=id, error=AccountNotFound)


    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_coming(self, account):
        raise NotImplementedError()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

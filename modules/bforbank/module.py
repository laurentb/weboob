# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
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
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.value import ValueBackendPassword, ValueDate
from .browser import BforbankBrowser


__all__ = ['BforbankModule']


class BforbankModule(Module, CapBankWealth):
    NAME = 'bforbank'
    DESCRIPTION = u'BforBank'
    MAINTAINER = u'Baptiste Delpey'
    EMAIL = 'b.delpey@hotmail.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code personnel', regexp=r'\d+$'),
                           ValueDate('birthdate', label='Date de naissance', formats=('%d/%m/%Y',))
                           )

    BROWSER = BforbankBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['birthdate'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get(),
                                   weboob=self.weboob)

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

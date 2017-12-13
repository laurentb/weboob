# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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


from weboob.capabilities.base import find_object
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Fortuneo


__all__ = ['FortuneoModule']


class FortuneoModule(Module, CapBankWealth):
    NAME = 'fortuneo'
    MAINTAINER = u'Gilles-Alexandre Quenot'
    EMAIL = 'gilles.quenot@gmail.com'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Fortuneo'
    CONFIG = BackendConfig(
                ValueBackendPassword('login',     label='Identifiant', masked=False, required=True),
                ValueBackendPassword('password',  label='Mot de passe', required=True))
    BROWSER = Fortuneo

    def create_default_browser(self):
        return self.create_browser(
                self.config['login'].get(),
                self.config['password'].get()
        )

    def iter_accounts(self):
        """Iter accounts"""
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        """Iter history of transactions on a specific account"""
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.get_investments(account)

# vim:ts=4:sw=4

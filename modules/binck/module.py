# -*- coding: utf-8 -*-

# Copyright(C) 2018 Arthur Huillet
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

from __future__ import unicode_literals


from weboob.capabilities.base import find_object
from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Binck


__all__ = ['BinckModule']


class BinckModule(Module, CapBankWealth):
    NAME = 'binck'
    MAINTAINER = 'Arthur Huillet'
    EMAIL = 'arthur.huillet+weboob@free.fr'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Binck'
    CONFIG = BackendConfig(
                ValueBackendPassword('login',     label='Identifiant', masked=False, required=True),
                ValueBackendPassword('password',  label='Mot de passe', required=True))
    BROWSER = Binck

    def create_default_browser(self):
        return self.create_browser(
                self.config['login'].get(),
                self.config['password'].get()
        )

    def get_account(self, id):
        """
        Get an account from its ID.

        :param id: ID of the account
        :type id: :class:`str`
        :rtype: :class:`Account`
        :raises: :class:`AccountNotFound`
        """
        return find_object(self.iter_accounts(), id=id, error=AccountNotFound)

    def iter_accounts(self):
        """
        Iter accounts.

        :rtype: iter[:class:`Account`]
        """
        return self.browser.get_accounts_list()

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_history(self, account):
        return self.browser.iter_history(account)

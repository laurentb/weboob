# -*- coding: utf-8 -*-

# Copyright(C) 2019      Antoine BOSSY
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
from weboob.capabilities.bank import CapBank, Account, AccountNotFound

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import TicketCesuBrowser


__all__ = ['TicketsCesuModule']


class TicketsCesuModule(Module, CapBank):
    NAME = 'ticketscesu'
    DESCRIPTION = 'Tickets CESU Edenred'
    MAINTAINER = 'Antoine BOSSY'
    EMAIL = 'mail+github@abossy.fr'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'

    BROWSER = TicketCesuBrowser

    CONFIG = BackendConfig(
        Value('login', label='Identifiant', masked=False),
        ValueBackendPassword('password', label='Code secret', required=True)
    )

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

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
        return self.browser.get_accounts()

    def iter_coming(self, account):
        """
        Iter coming transactions on a specific account.

        :param account: account to get coming transactions
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        :param account: account to get history
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        return self.browser.get_history(account.id)

    def iter_resources(self, objs, split_path):
        """
        Iter resources.

        Default implementation of this method is to return on top-level
        all accounts (by calling :func:`iter_accounts`).

        :param objs: type of objects to get
        :type objs: tuple[:class:`BaseObject`]
        :param split_path: path to discover
        :type split_path: :class:`list`
        :rtype: iter[:class:`BaseObject`]
        """
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()

        return []

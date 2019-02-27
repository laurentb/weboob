# -*- coding: utf-8 -*-

# Copyright(C) 2019      Damien Cassou
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

from __future__ import unicode_literals


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankTransfer, Account

from .browser import NefBrowser


__all__ = ['NefModule']


class NefModule(Module, CapBankTransfer):
    NAME = 'nef'
    DESCRIPTION = 'La Nef'
    MAINTAINER = 'Damien Cassou'
    EMAIL = 'damien@cassou.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.6'

    BROWSER = NefBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login', label='username', regexp='.+'),
                           ValueBackendPassword('password', label='Password'))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    # CapBank
    def iter_accounts(self):
        """
        Iter accounts.

        :rtype: iter[:class:`Account`]
        """
        return self.browser.iter_accounts_list()

    def iter_coming(self, account):
        """
        Iter coming transactions on a specific account.

        :param account: account to get coming transactions
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        return []

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        :param account: account to get history
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        return self.browser.iter_transactions_list(account)

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

    # CapBankTransfer
    def iter_transfer_recipients(self, account):
        """
        Iter recipients availables for a transfer from a specific account.

        :param account: account which initiate the transfer
        :type account: :class:`Account`
        :rtype: iter[:class:`Recipient`]
        :raises: :class:`AccountNotFound`
        """
        return self.browser.iter_recipients_list()

    def init_transfer(self, transfer, **params):
        """
        Initiate a transfer.

        :param :class:`Transfer`
        :rtype: :class:`Transfer`
        :raises: :class:`TransferError`
        """
        raise NotImplementedError()

    def execute_transfer(self, transfer, **params):
        """
        Execute a transfer.

        :param :class:`Transfer`
        :rtype: :class:`Transfer`
        :raises: :class:`TransferError`
        """
        raise NotImplementedError()

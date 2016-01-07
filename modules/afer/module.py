# -*- coding: utf-8 -*-

# Copyright(C) 2015      James GALT
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
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import AferBrowser


__all__ = ['AferModule']


class AferModule(Module, CapBank):
    NAME = 'afer'
    DESCRIPTION = u'afer website'
    MAINTAINER = u'James GALT'
    EMAIL = 'jgalt@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.2'

    BROWSER = AferBrowser
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Username', regexp='[A-z]\d+', masked=False),
                           ValueBackendPassword('password', label=u"mdp", regexp='\d+'))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())


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
        return self.browser.iter_accounts()

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
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        """
        Iter investment of a market account

        :param account: account to get investments
        :type account: :class:`Account`
        :rtype: iter[:class:`Investment`]
        :raises: :class:`AccountNotFound`
        """
        return self.browser.iter_investments(account)


    def iter_transfer_recipients(self, account):
        """
        Iter recipients availables for a transfer from a specific account.

        :param account: account which initiate the transfer
        :type account: :class:`Account`
        :rtype: iter[:class:`Recipient`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def transfer(self, account, recipient, amount, reason):
        """
        Make a transfer from an account to a recipient.

        :param account: account to take money
        :type account: :class:`Account`
        :param recipient: account to send money
        :type recipient: :class:`Recipient`
        :param amount: amount
        :type amount: :class:`decimal.Decimal`
        :param reason: reason of transfer
        :type reason: :class:`unicode`
        :rtype: :class:`Transfer`
        :raises: :class:`AccountNotFound`, :class:`TransferError`
        """
        raise NotImplementedError()


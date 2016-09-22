# -*- coding: utf-8 -*-

# Copyright(C) 2016      Benjamin Bouvier
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


from weboob.capabilities.bank import CapBank
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .browser import Number26Browser

__all__ = ['Number26Module']


class Number26Module(Module, CapBank):
    NAME = 'n26'
    DESCRIPTION = u'German online bank N26'
    MAINTAINER = u'Benjamin Bouvier'
    EMAIL = 'public+weboob@benj.me'
    LICENSE = 'AGPLv3+'
    VERSION = '1.2'

    BROWSER = Number26Browser

    CONFIG = BackendConfig(
                 Value('login', label='Email', regexp='.+'),
                 ValueBackendPassword('password', label='Password')
             )

    STORAGE = {'categories': {}}

    def get_categories(self):
        categories = self.storage.get("categories", None)
        if categories is None:
            categories = self.browser.get_categories()
            self.storage.set("categories", categories)
        return categories

    def create_default_browser(self):
        return Number26Browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        """
        Iter accounts.

        :rtype: iter[:class:`Account`]
        """
        return self.browser.get_accounts()

    def _restrict_level(self, split_path, lmax=0):
        pass

    def get_account(self, _id):
        """
        Get an account from its ID.

        :param id: ID of the account
        :type id: :class:`str`
        :rtype: :class:`Account`
        :raises: :class:`AccountNotFound`
        """
        return self.browser.get_account(_id)

    def iter_coming(self, account):
        """
        Iter coming transactions on a specific account.

        :param account: account to get coming transactions
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """

        categories = self.get_categories()
        return self.browser.get_coming(categories)

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        :param account: account to get history
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """

        categories = self.get_categories()
        return self.browser.get_transactions(categories)

    def iter_investment(self, account):
        """
        Iter investment of a market account

        :param account: account to get investments
        :type account: :class:`Account`
        :rtype: iter[:class:`Investment`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

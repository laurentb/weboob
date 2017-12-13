# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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


from weboob.capabilities.bank import CapBankWealth, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import AmundiBrowser

__all__ = ['AmundiModule']


class AmundiModule(Module, CapBankWealth):
    NAME = 'amundi'
    DESCRIPTION = u'amundi website'
    MAINTAINER = u'James GALT'
    EMAIL = 'james.galt.bi@gmail.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', regexp='\d+', masked=False),
                           ValueBackendPassword('password', label=u"Mot de passe", regexp='\d+'),
                           Value('website', label='Type de compte', default='ee',
                                choices={'ee': 'Amundi Epargne Entreprise',
                                        'tc': 'Amundi Tenue de Compte'}))

    BROWSER = AmundiBrowser

    def create_default_browser(self):
        w = {'ee': 'https://www.amundi-ee.com', 'tc': 'https://epargnants.amundi-tc.com'}
        return self.create_browser(w[self.config['website'].get()], self.config['login'].get(), self.config['password'].get())

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


    def iter_investment(self, account):
        """
        Iter investment of a market account

        :param account: account to get investments
        :type account: :class:`Account`
        :rtype: iter[:class:`Investment`]
        :raises: :class:`AccountNotFound`
        """
        for inv in self.browser.iter_investments(account):
            if inv.valuation != 0:
                yield inv

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        :param account: account to get history
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        return self.browser.iter_history(account)

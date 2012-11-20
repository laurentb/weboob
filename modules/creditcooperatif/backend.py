# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget, based on Romain Bignon work
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


from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.value import ValueBackendPassword, Value

from .browser import CreditCooperatif


__all__ = ['CreditCooperatifBackend']


class CreditCooperatifBackend(BaseBackend, ICapBank):
    NAME = 'creditcooperatif'
    MAINTAINER = u'Kevin Pouget'
    EMAIL = 'weboob@kevin.pouget.me'
    VERSION = '0.d'
    DESCRIPTION = u'Credit Cooperatif French bank website'
    LICENSE = 'AGPLv3+'
    auth_type = {"weak" : "Code confidentiel", 
                 "strong": "Sesame"}
    CONFIG = BackendConfig(Value('auth_type',  label='Authentication type', choices=auth_type, default="strong"),
                           ValueBackendPassword('login', label='Account ID', masked=False),
                           ValueBackendPassword('pin', label='One time pin'))
                           
    BROWSER = CreditCooperatif
    
    def create_default_browser(self):
        print self.config['login'].get()
        print self.config['auth_type'].get()
        
        return self.create_browser(self.config['login'].get(),
                                   self.config['pin'].get(),
                                   self.config['auth_type'].get() == "strong")

    def iter_accounts(self):
        with self.browser:
            return self.browser.get_accounts_list()

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)

        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        with self.browser:
            return self.browser.get_history(account)
        
    def iter_coming(self, account):
        with self.browser:
            return self.browser.get_coming(account)

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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
from weboob.tools.value import Value, ValueBackendPassword

from .browser import GroupamaBrowser


__all__ = ['GroupamaModule']


class GroupamaModule(Module, CapBankWealth):
    NAME = 'groupama'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = u'Groupama'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login',    label=u'Numéro client'), \
                           ValueBackendPassword('password', label=u"Code d'accès"))
    BROWSER = GroupamaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), \
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list(need_iban=True)

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(need_iban=True), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

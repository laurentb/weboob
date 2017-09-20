# -*- coding: utf-8 -*-

# Copyright(C) 2012      Gabriel Serme
# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from weboob.capabilities.bank import CapBankTransferAddRecipient, Account, AccountNotFound
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.contact import CapContact
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, ValueBool, Value

from .browser import BoursoramaBrowser


__all__ = ['BoursoramaModule']


class BoursoramaModule(Module, CapBankTransferAddRecipient, CapProfile, CapContact):
    NAME = 'boursorama'
    MAINTAINER = u'Gabriel Kerneis'
    EMAIL = 'gabriel@kerneis.info'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Boursorama'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Mot de passe'),
                           ValueBool('enable_twofactors',     label='Send validation sms', default=False),
                           Value('device',                    label='Device name', regexp='\w*', default=''),
                           Value('pin_code',                  label='Sms code', required=False),
                          )
    BROWSER = BoursoramaBrowser

    def create_default_browser(self):
        return self.create_browser(self.config)

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        for tr in self.browser.get_history(account):
            if not tr._is_coming:
                yield tr

    def iter_coming(self, account):
        for tr in self.browser.get_history(account, coming=True):
            if tr._is_coming:
                yield tr

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def get_profile(self):
        return self.browser.get_profile()

    def iter_contacts(self):
        return self.browser.get_advisor()

    def iter_transfer_recipients(self, account):
        if not isinstance(account, Account):
            account = self.get_account(account)
        return self.browser.iter_transfer_recipients(account)

    def init_transfer(self, transfer, **kwargs):
        return self.browser.init_transfer(transfer, **kwargs)

    def new_recipient(self, recipient, **kwargs):
        return self.browser.new_recipient(recipient, **kwargs)

    def execute_transfer(self, transfer, **kwargs):
        return self.browser.execute_transfer(transfer, **kwargs)

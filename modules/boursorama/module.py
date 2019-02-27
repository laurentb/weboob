# -*- coding: utf-8 -*-

# Copyright(C) 2012      Gabriel Serme
# Copyright(C) 2011      Gabriel Kerneis
# Copyright(C) 2010-2011 Jocelyn Jaubert
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

import re

from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, Account, AccountNotFound, CapCurrencyRate
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.contact import CapContact
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, ValueBool, Value

from .browser import BoursoramaBrowser


__all__ = ['BoursoramaModule']


class BoursoramaModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapProfile, CapContact, CapCurrencyRate):
    NAME = 'boursorama'
    MAINTAINER = u'Gabriel Kerneis'
    EMAIL = 'gabriel@kerneis.info'
    VERSION = '1.6'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Boursorama'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Mot de passe'),
                           ValueBool('enable_twofactors',     label='Send validation sms', default=False),
                           Value('device',                    label='Device name', regexp='\w*', default='weboob'),
                           Value('pin_code',                  label='Sms code', required=False, default=''),
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

    def transfer_check_label(self, old, new):
        # In the confirm page the '<' is interpeted like a html tag
        # If no '>' is present the following chars are deleted
        # Else: inside '<>' chars are deleted
        old = re.sub(r'<[^>]*>', '', old).strip()
        old = old.split('<')[0]
        return super(BoursoramaModule, self).transfer_check_label(old, new)

    def iter_currencies(self):
        return self.browser.iter_currencies()

    def get_rate(self, currency_from, currency_to):
        return self.browser.get_rate(currency_from, currency_to)

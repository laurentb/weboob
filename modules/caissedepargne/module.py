# -*- coding: utf-8 -*-

# Copyright(C) 2012-2017 Romain Bignon
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

from collections import OrderedDict
import re

from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, Account, RecipientNotFound
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .proxy_browser import ProxyBrowser

__all__ = ['CaisseEpargneModule']


class CaisseEpargneModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapContact, CapProfile):
    NAME = 'caissedepargne'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'Caisse d\'Épargne'
    LICENSE = 'AGPLv3+'
    BROWSER = ProxyBrowser
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.caisse-epargne.fr':     u'Caisse d\'Épargne',
        'www.banquebcp.fr':          u'Banque BCP',
        }.items(), key=lambda k_v: (k_v[1], k_v[0]))])
    CONFIG = BackendConfig(Value('website',  label='Banque', choices=website_choices, default='www.caisse-epargne.fr'),
                           ValueBackendPassword('login',    label='Identifiant client', masked=False),
                           ValueBackendPassword('password', label='Code personnel', regexp='\d+'),
                           Value('nuser',                   label='User ID (optional)', default=''),
                           Value('pincode',                 label='pincode', required=False))

    def create_default_browser(self):
        return self.create_browser(nuser=self.config['nuser'].get(),
                                   username=self.config['login'].get(),
                                   password=self.config['password'].get(),
                                   domain=self.config['website'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account
        for account in self.browser.get_loans_list():
            yield account

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def iter_contacts(self):
        return self.browser.get_advisor()

    def get_profile(self):
        return self.browser.get_profile()

    def iter_transfer_recipients(self, origin_account):
        if not isinstance(origin_account, Account):
            origin_account = find_object(self.iter_accounts(), id=origin_account, error=AccountNotFound)
        return self.browser.iter_recipients(origin_account)

    def init_transfer(self, transfer, **params):
        self.logger.info('Going to do a new transfer')
        transfer.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z/\-\?:\(\)\.,\'\+ ]+', '', transfer.label).split()).upper()
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        return self.browser.init_transfer(account, recipient, transfer)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def new_recipient(self, recipient, **params):
        #recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z:\/\-\?\(\)\.,\'\+ ]+', '', recipient.label).split())
        return self.browser.new_recipient(recipient, **params)

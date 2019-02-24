# -*- coding: utf-8 -*-

# Copyright(C) 2012-2017 Romain Bignon
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

from collections import OrderedDict
import re
from decimal import Decimal

from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, Account, RecipientNotFound
from weboob.capabilities.bill import (
    CapDocument, Subscription, SubscriptionNotFound,
    Document, DocumentNotFound, DocumentTypes,
)
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .proxy_browser import ProxyBrowser

__all__ = ['CaisseEpargneModule']


class CaisseEpargneModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapDocument, CapContact, CapProfile):
    NAME = 'caissedepargne'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
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
                           Value('nuser',                   label='User ID (optional)', default='', regexp='\d{0,8}'),
                           Value('pincode',                 label='pincode', required=False))

    accepted_document_types = (DocumentTypes.OTHER,)

    def create_default_browser(self):
        return self.create_browser(nuser=self.config['nuser'].get(),
                                   username=self.config['login'].get(),
                                   password=self.config['password'].get(),
                                   domain=self.config['website'].get(),
                                   weboob=self.weboob)

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
            origin_account = self.get_account(origin_account)
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

        transfer.amount = transfer.amount.quantize(Decimal(10) ** -2)

        return self.browser.init_transfer(account, recipient, transfer)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def new_recipient(self, recipient, **params):
        #recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z:\/\-\?\(\)\.,\'\+ ]+', '', recipient.label).split())
        return self.browser.new_recipient(recipient, **params)

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def get_document(self, _id):
        subscription_id = _id.split('_')[0]
        subscription = self.get_subscription(subscription_id)
        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def iter_subscription(self):
        return self.browser.iter_subscription()

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)

        return self.browser.iter_documents(subscription)

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)

        if document.url is NotAvailable:
            return

        return self.browser.download_document(document)

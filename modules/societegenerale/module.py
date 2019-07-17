# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
# Copyright(C) 2012-2013 Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

import re
from decimal import Decimal
from datetime import timedelta

from weboob.capabilities.bank import (
    CapBankWealth, CapBankTransferAddRecipient, AccountNotFound,
    Account, RecipientNotFound,
)
from weboob.capabilities.bill import (
    CapDocument, Subscription, SubscriptionNotFound,
    Document, DocumentNotFound, DocumentTypes,
)
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.base import find_object, NotAvailable, strict_find_object

from .browser import SocieteGenerale
from .sgpe.browser import SGEnterpriseBrowser, SGProfessionalBrowser


__all__ = ['SocieteGeneraleModule']


class SocieteGeneraleModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapContact, CapProfile, CapDocument):
    NAME = 'societegenerale'
    MAINTAINER = u'Jocelyn Jaubert'
    EMAIL = 'jocelyn.jaubert@gmail.com'
    VERSION = '1.6'
    LICENSE = 'LGPLv3+'
    DESCRIPTION = u'Société Générale'
    CONFIG = BackendConfig(
        ValueBackendPassword('login',      label='Code client', masked=False),
        ValueBackendPassword('password',   label='Code secret'),
        Value('website', label='Type de compte', default='par',
              choices={'par': 'Particuliers', 'pro': 'Professionnels', 'ent': 'Entreprises'}))

    accepted_document_types = (DocumentTypes.STATEMENT, DocumentTypes.RIB)

    def create_default_browser(self):
        b = {'par': SocieteGenerale, 'pro': SGProfessionalBrowser, 'ent': SGEnterpriseBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_coming(self, account):
        if hasattr(self.browser, 'get_cb_operations'):
            transactions = list(self.browser.get_cb_operations(account))
            return sorted_transactions(transactions)
        return self.browser.iter_coming(account)

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_contacts(self):
        if not hasattr(self.browser, 'get_advisor'):
            raise NotImplementedError()
        return self.browser.get_advisor()

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()
        return self.browser.get_profile()

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() not in ('par', 'pro'):
            raise NotImplementedError()
        if not isinstance(origin_account, Account):
            origin_account = find_object(self.iter_accounts(), id=origin_account, error=AccountNotFound)
        return self.browser.iter_recipients(origin_account)

    def new_recipient(self, recipient, **params):
        if self.config['website'].get() not in ('par', 'pro'):
            raise NotImplementedError()
        recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z:\/\-\?\(\)\.,\'\+ ]+', '', recipient.label).split())
        return self.browser.new_recipient(recipient, **params)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() not in ('par', 'pro'):
            raise NotImplementedError()
        transfer.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z ]+', '', transfer.label).split())
        self.logger.info('Going to do a new transfer')

        account = strict_find_object(self.iter_accounts(), iban=transfer.account_iban)
        if not account:
            account = strict_find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        recipient = strict_find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id)
        if not recipient:
            recipient = strict_find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)

        transfer.amount = transfer.amount.quantize(Decimal('.01'))
        return self.browser.init_transfer(account, recipient, transfer)

    def execute_transfer(self, transfer, **params):
        if self.config['website'].get() not in ('par', 'pro'):
            raise NotImplementedError()
        return self.browser.execute_transfer(transfer)

    def transfer_check_exec_date(self, old_exec_date, new_exec_date):
        return old_exec_date <= new_exec_date <= old_exec_date + timedelta(days=4)

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

    def iter_documents_by_types(self, subscription, accepted_types):
        return self.browser.iter_documents_by_types(subscription, accepted_types)

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)

        if document.url is NotAvailable:
            return

        return self.browser.open(document.url).content

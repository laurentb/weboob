# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013  Romain Bignon, Pierre Mazière
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


from decimal import Decimal
from functools import wraps
import re

from weboob.capabilities.bank import CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, \
                                     RecipientNotFound, TransferError, Account
from weboob.capabilities.bill import CapDocument, Subscription, SubscriptionNotFound, \
                                     Document, DocumentNotFound, DocumentTypes
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.base import find_object, NotAvailable

from .browser import LCLBrowser, LCLProBrowser, ELCLBrowser
from .enterprise.browser import LCLEnterpriseBrowser, LCLEspaceProBrowser


__all__ = ['LCLModule']


def only_for_websites(*cfg):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.config['website'].get() not in cfg:
                raise NotImplementedError()

            return func(self, *args, **kwargs)

        return wrapper
    return decorator


class LCLModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapContact, CapProfile, CapDocument):
    NAME = 'lcl'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'LCL'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code personnel'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers',
                                          'pro': 'Professionnels',
                                          'ent': 'Entreprises',
                                          'esp': 'Espace Pro',
                                          'elcl': 'e.LCL'}))
    BROWSER = LCLBrowser

    accepted_doc_types = (DocumentTypes.STATEMENT, DocumentTypes.NOTICE, DocumentTypes.REPORT, DocumentTypes.OTHER)

    def create_default_browser(self):
        # assume all `website` option choices are defined here
        browsers = {'par': LCLBrowser,
                    'pro': LCLProBrowser,
                    'elcl': ELCLBrowser,
                    'ent': LCLEnterpriseBrowser,
                    'esp': LCLEspaceProBrowser}

        website_value = self.config['website']
        self.BROWSER = browsers.get(website_value.get(),
                                    browsers[website_value.default])

        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_coming(self, account):
        transactions = sorted_transactions(self.browser.get_cb_operations(account))
        return transactions

    def iter_history(self, account):
        transactions = sorted_transactions(self.browser.get_history(account))
        return transactions

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    @only_for_websites('par', 'pro', 'elcl')
    def iter_transfer_recipients(self, origin_account):
        if not isinstance(origin_account, Account):
            origin_account = find_object(self.iter_accounts(), id=origin_account, error=AccountNotFound)
        return self.browser.iter_recipients(origin_account)

    @only_for_websites('par', 'pro', 'elcl')
    def new_recipient(self, recipient, **params):
        # Recipient label has max 15 alphanumrical chars.
        recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z ]+', '', recipient.label).split())[:15]
        return self.browser.new_recipient(recipient, **params)

    @only_for_websites('par', 'pro', 'elcl')
    def init_transfer(self, transfer, **params):
        # There is a check on the website, transfer can't be done with too long reason.
        if transfer.label:
            transfer.label = transfer.label[:30]

        self.logger.info('Going to do a new transfer')
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        if transfer.recipient_iban:
            recipient = find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban, error=RecipientNotFound)
        else:
            recipient = find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        try:
            # quantize to show 2 decimals.
            amount = Decimal(transfer.amount).quantize(Decimal(10) ** -2)
        except (AssertionError, ValueError):
            raise TransferError('something went wrong')

        return self.browser.init_transfer(account, recipient, amount, transfer.label, transfer.exec_date)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def transfer_check_label(self, old, new):
        old = re.sub(r"[/<\?='!\+:]", '', old).strip()
        old = old.encode('latin-1', errors='replace').decode('latin-1')
        return super(LCLModule, self).transfer_check_label(old, new)

    @only_for_websites('par')
    def iter_contacts(self):
        return self.browser.get_advisor()

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()

        profile = self.browser.get_profile()
        if profile:
            return profile
        raise NotImplementedError()

    @only_for_websites('par')
    def get_document(self, _id):
        return find_object(self.iter_documents(None), id=_id, error=DocumentNotFound)

    @only_for_websites('par')
    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    @only_for_websites('par')
    def iter_bills(self, subscription):
        return self.iter_documents(None)

    @only_for_websites('par')
    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)

        return self.browser.iter_documents(subscription)

    @only_for_websites('par')
    def iter_subscription(self):
        return self.browser.iter_subscriptions()

    @only_for_websites('par')
    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)
        if document.url is NotAvailable:
            return

        return self.browser.open(document.url).content

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

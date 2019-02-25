# -*- coding: utf-8 -*-

# Copyright(C) 2010-2016 Romain Bignon
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
from decimal import Decimal
from datetime import datetime, timedelta

from weboob.capabilities.bank import (
    CapBankWealth, CapBankTransferAddRecipient, AccountNotFound, Account, RecipientNotFound,
    TransferInvalidLabel,
)
from weboob.capabilities.messages import CapMessages, Thread
from weboob.capabilities.contact import CapContact
from weboob.capabilities.profile import CapProfile
from weboob.capabilities.base import find_object, strict_find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value, ValueBool

from .enterprise.browser import BNPEnterprise
from .company.browser import BNPCompany
from .pp.browser import BNPPartPro, HelloBank


__all__ = ['BNPorcModule']


class BNPorcModule(Module, CapBankWealth, CapBankTransferAddRecipient, CapMessages, CapContact, CapProfile):
    NAME = 'bnporc'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'BNP Paribas'
    CONFIG = BackendConfig(
        ValueBackendPassword('login',      label=u'Numéro client', masked=False),
        ValueBackendPassword('password',   label=u'Code secret', regexp='^(\d{6})$'),
        ValueBool('rotating_password',     label=u'Automatically renew password every 100 connections', default=False),
        Value('website', label='Type de compte', default='pp',
              choices={'pp': 'Particuliers/Professionnels',
                       'hbank': 'HelloBank',
                       'ent': 'Entreprises',
                       'ent2': 'Entreprises et PME (nouveau site)'}))
    STORAGE = {'seen': []}

    # Store the messages *list* for this duration
    CACHE_THREADS = timedelta(seconds=3 * 60 * 60)

    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)
        self._threads = None
        self._threads_age = datetime.utcnow()

    def create_default_browser(self):
        b = {'ent': BNPEnterprise, 'ent2': BNPCompany, 'pp': BNPPartPro, 'hbank': HelloBank}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        return self.browser.iter_coming_operations(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_transfer_recipients(self, origin_account):
        if self.config['website'].get() != 'pp':
            raise NotImplementedError()
        if isinstance(origin_account, Account):
            origin_account = origin_account.id
        return self.browser.iter_recipients(origin_account)

    def new_recipient(self, recipient, **params):
        if self.config['website'].get() != 'pp':
            raise NotImplementedError()
        # Recipient label has max 70 chars.
        recipient.label = ' '.join(w for w in re.sub('[^0-9a-zA-Z-,\.: ]+', '', recipient.label).split())[:70]
        return self.browser.new_recipient(recipient, **params)

    def init_transfer(self, transfer, **params):
        if self.config['website'].get() != 'pp':
            raise NotImplementedError()

        if transfer.label is None:
            raise TransferInvalidLabel()

        self.logger.info('Going to do a new transfer')
        if transfer.account_iban:
            account = find_object(self.iter_accounts(), iban=transfer.account_iban, error=AccountNotFound)
        else:
            account = find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        recipient = strict_find_object(self.iter_transfer_recipients(account.id), iban=transfer.recipient_iban)
        if not recipient:
            recipient = strict_find_object(self.iter_transfer_recipients(account.id), id=transfer.recipient_id, error=RecipientNotFound)

        assert account.id.isdigit()
        # quantize to show 2 decimals.
        amount = Decimal(transfer.amount).quantize(Decimal(10) ** -2)

        return self.browser.init_transfer(account, recipient, amount, transfer.label, transfer.exec_date)

    def execute_transfer(self, transfer, **params):
        return self.browser.execute_transfer(transfer)

    def transfer_check_recipient_id(self, old, new):
        # external recipient id can change, check the iban in recipient id
        iban = re.search(r'([A-Z]{2}[A-Z\d]+)', old)
        if iban:
            # external recipients id
            iban = iban.group(1)
            return iban in new
        else:
            # iternal recipients id
            return old == new

    def iter_contacts(self):
        if not hasattr(self.browser, 'get_advisor'):
            raise NotImplementedError()

        for advisor in self.browser.get_advisor():
            yield advisor

    def get_profile(self):
        if not hasattr(self.browser, 'get_profile'):
            raise NotImplementedError()
        return self.browser.get_profile()

    def iter_threads(self, cache=False):
        """
        If cache is False, always fetch the threads from the website.
        """
        old = self._threads_age < datetime.utcnow() - self.CACHE_THREADS
        threads = self._threads
        if not cache or threads is None or old:
            threads = list(self.browser.iter_threads())
            # the website is stupid and does not have the messages in the proper order
            threads = sorted(threads, key=lambda t: t.date, reverse=True)
            self._threads = threads
        seen = self.storage.get('seen', default=[])
        for thread in threads:
            if thread.id not in seen:
                thread.root.flags |= thread.root.IS_UNREAD
            else:
                thread.root.flags &= ~thread.root.IS_UNREAD
            yield thread

    def fill_thread(self, thread, fields=None):
        if fields is None or 'root' in fields:
            return self.get_thread(thread)

    def get_thread(self, _id):
        if self.config['website'].get() != 'ppold':
            raise NotImplementedError()

        if isinstance(_id, Thread):
            thread = _id
            _id = thread.id
        else:
            thread = Thread(_id)
        thread = self.browser.get_thread(thread)
        return thread

    def iter_unread_messages(self):
        if self.config['website'].get() != 'ppold':
            raise NotImplementedError()

        threads = list(self.iter_threads(cache=True))
        for thread in threads:
            if thread.root.flags & thread.root.IS_UNREAD:
                thread = self.fillobj(thread) or thread
                yield thread.root

    def set_message_read(self, message):
        self.storage.get('seen', default=[]).append(message.thread.id)
        self.storage.save()

    OBJECTS = {Thread: fill_thread}

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
# Copyright(C) 2013-2015 Christophe Lampin

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
from datetime import datetime, timedelta

from weboob.capabilities.bank import CapBank, AccountNotFound, Account, Recipient
from weboob.capabilities.messages import CapMessages, Thread
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import HelloBank


__all__ = ['HelloBankModule']


class HelloBankModule(Module, CapBank, CapMessages):
    NAME = 'hellobank'
    MAINTAINER = u'Christophe Lampin'
    EMAIL = 'weboob@lampin.net'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Hello Bank!'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Code secret', regexp='^(\d{6}|)$'))
    BROWSER = HelloBank
    STORAGE = {'seen': []}

    # Store the messages *list* for this duration
    CACHE_THREADS = timedelta(seconds=3 * 60 * 60)

    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)
        self._threads = None
        self._threads_age = datetime.utcnow()

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        if not _id.isdigit():
            raise AccountNotFound()
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        with self.browser:
            return self.browser.iter_history(account)

    def iter_coming(self, account):
        with self.browser:
            return self.browser.iter_coming_operations(account)

    def iter_transfer_recipients(self, ignored):
        for account in self.browser.get_transfer_accounts().itervalues():
            recipient = Recipient()
            recipient.id = account.id
            recipient.label = account.label
            yield recipient

    def transfer(self, account, to, amount, reason=None):
        if isinstance(account, Account):
            account = account.id

        try:
            assert account.isdigit()
            assert to.isdigit()
            amount = Decimal(amount)
        except (AssertionError, ValueError):
            raise AccountNotFound()

        with self.browser:
            return self.browser.transfer(account, to, amount, reason)

    def iter_threads(self, cache=False):
        """
        If cache is False, always fetch the threads from the website.
        """
        old = self._threads_age < datetime.utcnow() - self.CACHE_THREADS
        threads = self._threads
        if not cache or threads is None or old:
            with self.browser:
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
        if isinstance(_id, Thread):
            thread = _id
            _id = thread.id
        else:
            thread = Thread(_id)
        with self.browser:
            thread = self.browser.get_thread(thread)
        return thread

    def iter_unread_messages(self):
        threads = list(self.iter_threads(cache=True))
        for thread in threads:
            if thread.root.flags & thread.root.IS_UNREAD:
                thread = self.fillobj(thread) or thread
                yield thread.root

    def set_message_read(self, message):
        self.storage.get('seen', default=[]).append(message.thread.id)
        self.storage.save()

    OBJECTS = {Thread: fill_thread}

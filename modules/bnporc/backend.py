# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.bank import ICapBank, AccountNotFound, Account, Recipient
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import BNPorc


__all__ = ['BNPorcBackend']


class BNPorcBackend(BaseBackend, ICapBank):
    NAME = 'bnporc'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.b'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'BNP Paribas French bank website'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Account ID', masked=False),
                           ValueBackendPassword('password',   label='Password', regexp='^(\d{6}|)$'),
                           ValueBackendPassword('rotating_password', default='',
                                 label='Password to set when the allowed uses are exhausted (6 digits)',
                                 regexp='^(\d{6}|)$'))
    BROWSER = BNPorc

    def create_default_browser(self):
        if self.config['rotating_password'].get().isdigit() and len(self.config['rotating_password'].get()) == 6:
            rotating_password = self.config['rotating_password'].get()
        else:
            rotating_password = None
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get(),
                                   password_changed_cb=self._password_changed_cb,
                                   rotating_password=rotating_password)

    def _password_changed_cb(self, old, new):
        self.config['password'].set(new)
        self.config['rotating_password'].set(old)
        self.config.save()

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
            return self.browser.iter_history(account.link_id)

    def iter_operations(self, account):
        with self.browser:
            return self.browser.iter_coming_operations(account.link_id)

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
            amount = float(amount)
        except (AssertionError, ValueError):
            raise AccountNotFound()

        with self.browser:
            return self.browser.transfer(account, to, amount, reason)

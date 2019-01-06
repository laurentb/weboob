# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankWealth, Account
from weboob.capabilities.base import find_object
from weboob.capabilities.bill import (
    CapDocument, Subscription, SubscriptionNotFound, DocumentNotFound, Document,
)
from weboob.capabilities.profile import CapProfile

from .browser import BoldenBrowser


__all__ = ['BoldenModule']


class BoldenModule(Module, CapBankWealth, CapDocument, CapProfile):
    NAME = 'bolden'
    DESCRIPTION = 'Bolden'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = BoldenBrowser

    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Email', masked=False),
        ValueBackendPassword('password', label='Mot de passe'),
    )

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investments()

    def get_profile(self):
        return self.browser.get_profile()

    def iter_subscription(self):
        sub = Subscription()
        sub.id = '_bolden_'
        sub.subscriber = self.get_profile().name
        sub.label = 'Bolden %s' % sub.subscriber
        return [sub]

    def get_subscription(self, _id):
        if _id == '_bolden_':
            return self.iter_subscription()[0]
        raise SubscriptionNotFound()

    def iter_documents(self, sub):
        if not isinstance(sub, Subscription):
            sub = self.get_subscription(sub)
        return self.browser.iter_documents()

    def get_document(self, id):
        return find_object(self.browser.iter_documents(), id=id, error=DocumentNotFound)

    def download_document(self, doc):
        if not isinstance(doc, Document):
            doc = self.get_document(doc)
        return self.browser.open(doc.url).content

    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)
            return self.iter_accounts()
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()

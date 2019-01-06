# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015      Christophe Lampin
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

from weboob.capabilities.bill import CapDocument, SubscriptionNotFound, DocumentNotFound, Subscription, Bill
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import AmeliBrowser

__all__ = ['AmeliModule']


class AmeliModule(Module, CapDocument):
    NAME = 'ameli'
    DESCRIPTION = 'Ameli website: French Health Insurance'
    MAINTAINER = 'Christophe Lampin'
    EMAIL = 'weboob@lampin.net'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    BROWSER = AmeliBrowser
    CONFIG = BackendConfig(ValueBackendPassword('login', label='Numero de SS', regexp=r'^\d{13}$', masked=False),
                           ValueBackendPassword('password', label='Password', masked=True))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.iter_subscription_list()

    def get_subscription(self, _id):
        subscription = self.browser.get_subscription(_id)
        if not subscription:
            raise SubscriptionNotFound()
        else:
            return subscription

    def iter_documents_history(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_history(subscription)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def get_document(self, id):
        bill = self.browser.get_document(id)
        if not bill:
            raise DocumentNotFound()
        else:
            return bill

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        response = self.browser.open(bill.url, stream=True)
        if not response or response.headers['content-type'] != "application/pdf":
            return None
        return response.content

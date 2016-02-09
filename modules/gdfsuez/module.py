# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mathieu Jourdan
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

from weboob.capabilities.bill import CapDocument, SubscriptionNotFound,\
    DocumentNotFound, Subscription, Bill
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import GdfSuez

__all__ = ['GdfSuezModule']


class GdfSuezModule(Module, CapDocument):
    NAME = 'gdfsuez'
    MAINTAINER = u'Mathieu Jourdan'
    EMAIL = 'mathieu.jourdan@gresille.org'
    VERSION = '1.2'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'GDF-Suez French energy provider'
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='Account ID (e-mail)',
                                                masked=False),
                           ValueBackendPassword('password',
                                                label='Password',
                                                masked=True)
                           )
    BROWSER = GdfSuez

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        for subscription in self.browser.get_subscription_list():
            yield subscription

    def get_subscription(self, _id):
        if not _id.isdigit():
            raise SubscriptionNotFound()
        with self.browser:
            subscription = self.browser.get_subscription(_id)
        if not subscription:
            raise SubscriptionNotFound()
        else:
            return subscription

    def iter_documents_history(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            for history in self.browser.get_history(subscription):
                yield history

    def get_details(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            for detail in self.browser.get_details(subscription):
                yield detail

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        with self.browser:
            for bill in self.browser.iter_documents():
                yield bill

    def get_document(self, id):
        with self.browser:
            bill = self.browser.get_document(id)
        if not bill:
            raise DocumentNotFound()
        else:
            return bill

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        with self.browser:
            return self.browser.readurl(bill._url)

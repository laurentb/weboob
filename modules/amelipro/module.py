# -*- coding: utf-8 -*-

# Copyright(C) 2013-2015      Christophe Lampin
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

from weboob.capabilities.bill import DocumentTypes, CapDocument, SubscriptionNotFound, DocumentNotFound, Subscription, Bill
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from .browser import AmeliProBrowser

__all__ = ['AmeliProModule']

class AmeliProModule(Module, CapDocument):
    NAME = 'amelipro'
    DESCRIPTION = u'Ameli website: French Health Insurance for Professionals'
    MAINTAINER = u'Christophe Lampin'
    EMAIL = 'weboob@lampin.net'
    VERSION = '2.1'
    LICENSE = 'LGPLv3+'
    BROWSER = AmeliProBrowser
    CONFIG = BackendConfig(ValueBackendPassword('login',
                                                label='numero de SS',
                                                masked=False),
                           ValueBackendPassword('password',
                                                label='Password',
                                                masked=True)
                           )

    accepted_document_types = (DocumentTypes.BILL,)

    def create_default_browser(self):
        self.logger.settings['save_responses'] = False # Set to True to help debugging
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.get_subscription_list()

    def get_subscription(self, _id):
        if not _id.isdigit():
            raise SubscriptionNotFound()
        subscription = self.browser.get_subscription(_id)
        if not subscription:
            raise SubscriptionNotFound()
        else:
            return subscription

    def iter_documents_history(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_history(subscription)

    def get_details(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.get_details(subscription)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents()

    def get_document(self, id):
        bill = self.browser.get_document(id)
        if not bill:
            raise DocumentNotFound()
        else:
            return bill

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        return self.browser.download_document(bill)

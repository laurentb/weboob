# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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


from weboob.capabilities.bill import CapDocument, Subscription, Bill, SubscriptionNotFound, DocumentNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import LdlcBrowser


__all__ = ['LdlcModule']


class LdlcModule(Module, CapDocument):
    NAME = 'ldlc'
    DESCRIPTION = u'ldlc website'
    MAINTAINER = u'Vincent Paredes'
    EMAIL = 'vparedes@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(Value('login', label='Email'),
                       ValueBackendPassword('password', label='Password'),
                       Value('website', label='Site web', default='part',
                                                 choices={'pro': 'Professionnels',
                                                     'part': 'Particuliers'}))


    BROWSER = LdlcBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_subscription(self):
        return self.browser.get_subscription_list()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def get_document(self, _id):
        subid = _id.rsplit('_', 1)[0]
        subscription = self.get_subscription(subid)

        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def download_document(self, bill):
        if not isinstance(bill, Bill):
            bill = self.get_document(bill)
        return self.browser.open(bill.url).content

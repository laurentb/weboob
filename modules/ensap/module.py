# -*- coding: utf-8 -*-

# Copyright(C) 2017      Juliette Fourcot
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

from __future__ import unicode_literals

from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.base import find_object
from weboob.capabilities.bill import CapDocument, SubscriptionNotFound,\
                                     Document, DocumentNotFound
from weboob.tools.value import Value, ValueBackendPassword

from .browser import EnsapBrowser


__all__ = ['EnsapModule']


class EnsapModule(Module, CapDocument):
    NAME = 'ensap'
    DESCRIPTION = u'ensap website'
    MAINTAINER = u'Juliette Fourcot'
    EMAIL = 'juliette@fourcot.fr'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'

    BROWSER = EnsapBrowser
    CONFIG = BackendConfig(Value('login', label='User ID',
                                 regexp='[0-9]{15}', required=True),
                           ValueBackendPassword('password', label='Password'))

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def get_document(self, _id):
        return find_object(self.iter_documents(None), id=_id,
                           error=DocumentNotFound)

    def get_subscription(self, _id):
        return find_object(self.browser.iter_subscription(), id=_id,
                           error=SubscriptionNotFound)

    def iter_documents(self, subscription):
        if isinstance(subscription, basestring):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    def iter_subscription(self):
        return self.browser.iter_subscription()

    def download_document(self, doc):
        if not isinstance(doc, Document):
            doc = self.get_document(doc)
        return self.browser.open(doc.url).content

# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.bill import CapDocument, Document, DocumentTypes, SubscriptionNotFound, DocumentNotFound, Subscription
from weboob.tools.value import ValueBackendPassword

from .browser import AmeliBrowser


__all__ = ['AmeliModule']


class AmeliModule(Module, CapDocument):
    NAME = 'ameli'
    DESCRIPTION = "le site de l'Assurance Maladie en ligne"
    MAINTAINER = 'Florian Duguet'
    EMAIL = 'florian.duguet@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'

    BROWSER = AmeliBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login', label='Mon numero de sécurité sociale', regexp=r'^\d{13}$', masked=False),
                           ValueBackendPassword('password', label='Mon code (4 à 13 chiffres)', regexp=r'^\d{4,13}', masked=True))

    accepted_document_types = (DocumentTypes.BILL,)

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def iter_subscription(self):
        return self.browser.iter_subscription()

    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)

        return self.browser.iter_documents(subscription)

    def get_document(self, _id):
        subid = _id.rsplit('_', 1)[0]
        subscription = self.get_subscription(subid)
        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)

        return self.browser.open(document.url).content

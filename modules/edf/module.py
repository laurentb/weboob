# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.capabilities.bill import DocumentTypes, CapDocument, Subscription, Document, SubscriptionNotFound, DocumentNotFound
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.profile import CapProfile

from .par.browser import EdfBrowser
from .pro.proxy_browser import ProxyBrowser


__all__ = ['EdfModule']


class EdfModule(Module, CapDocument, CapProfile):
    NAME = 'edf'
    DESCRIPTION = u'EDF'
    MAINTAINER = u'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(Value('login', label='E-mail ou Identifiant'),
                           ValueBackendPassword('password', label='Mot de passe'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particulier', 'pro': 'Entreprise'}),
                           Value('otp', label='Entrez le code reçu par SMS', required=False))

    accepted_document_types = (DocumentTypes.BILL,)

    def create_default_browser(self):
        browsers = {'pro': ProxyBrowser, 'par': EdfBrowser}
        self.BROWSER = browsers[self.config['website'].get()]

        return self.create_browser(self.config)

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

    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)
        return self.browser.download_document(document)

    def get_profile(self):
        return self.browser.get_profile()

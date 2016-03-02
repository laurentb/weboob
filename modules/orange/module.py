# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


from weboob.capabilities.bill import CapDocument, Subscription, Document, SubscriptionNotFound, DocumentNotFound
from weboob.capabilities.messages import CantSendMessage, CapMessages, CapMessagesPost
from weboob.capabilities.base import find_object, NotAvailable
from weboob.capabilities.account import CapAccount, StatusField
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import OrangeBrowser
from .bill.browser import OrangeBillBrowser


__all__ = ['OrangeModule']

# We need to have a switcher, CapMessages use a browser1 and
# CapDocument use a browser2
# This will be remove when CapMessages use a browser2
def browser_switcher(b):
    def set_browser(func):
        def func_wrapper(*args, **kwargs):
            self = args[0]
            if self._browser is None or type(self._browser) != b:
                self.BROWSER = b
                try:
                    self._browser = self._browsers[b]
                except KeyError:
                    self._browsers[b] = self.create_default_browser()
                    self._browser = self._browsers[b]
            return func(*args, **kwargs)
        return func_wrapper
    return set_browser


class OrangeModule(Module, CapAccount, CapMessages, CapMessagesPost, CapDocument):
    NAME = 'orange'
    MAINTAINER = u'Lucas Nussbaum'
    EMAIL = 'lucas@lucas-nussbaum.net'
    VERSION = '1.2'
    DESCRIPTION = 'Orange French mobile phone provider'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login', label='Login'),
                           ValueBackendPassword('password', label='Password'),
                           Value('phonenumber', label='Phone number', default='')
                           )
    ACCOUNT_REGISTER_PROPERTIES = None
    BROWSER = OrangeBrowser


    def __init__(self, *args, **kwargs):
        self._browsers = dict()
        super(OrangeModule, self).__init__(*args, **kwargs)

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    @browser_switcher(OrangeBrowser)
    def get_account_status(self):
       return (StatusField('nb_remaining_free_sms', 'Number of remaining free SMS',
                                self.browser.get_nb_remaining_free_sms()),)

    @browser_switcher(OrangeBrowser)
    def post_message(self, message):
        if not message.content.strip():
            raise CantSendMessage(u'Message content is empty.')
        self.browser.post_message(message, self.config['phonenumber'].get())

    @browser_switcher(OrangeBillBrowser)
    def iter_subscription(self):
        return self.browser.get_subscription_list()

    @browser_switcher(OrangeBillBrowser)
    def get_subscription(self, _id):
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    @browser_switcher(OrangeBillBrowser)
    def get_document(self, _id):
        subid = _id.rsplit('_', 1)[0]
        subscription = self.get_subscription(subid)
        return find_object(self.iter_documents(subscription), id=_id, error=DocumentNotFound)

    @browser_switcher(OrangeBillBrowser)
    def iter_documents(self, subscription):
        if not isinstance(subscription, Subscription):
            subscription = self.get_subscription(subscription)
        return self.browser.iter_documents(subscription)

    @browser_switcher(OrangeBillBrowser)
    def download_document(self, document):
        if not isinstance(document, Document):
            document = self.get_document(document)
        if document._url is NotAvailable:
            return
        return self.browser.open(document._url).content

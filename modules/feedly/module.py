# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.collection import CapCollection
from weboob.capabilities.messages import CapMessages, Message, Thread
from weboob.tools.value import Value, ValueBackendPassword

from .browser import FeedlyBrowser
from .google import GoogleBrowser

__all__ = ['FeedlyModule']


class FeedlyModule(Module, CapMessages, CapCollection):
    NAME = 'feedly'
    DESCRIPTION = u'handle the popular RSS reading service Feedly'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'
    STORAGE = {'seen': []}
    CONFIG = BackendConfig(Value('username', label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''))

    BROWSER = FeedlyBrowser

    def iter_resources(self, objs, split_path):
        collection = self.get_collection(objs, split_path)
        if collection.path_level == 0:
            return self.browser.get_categories()

        if collection.path_level == 1:
            return self.browser.get_feeds(split_path[0])

        if collection.path_level == 2:
            url = self.browser.get_feed_url(split_path[0], split_path[1])
            threads = []
            for article in self.browser.get_unread_feed(url):
                thread = self.get_thread(article.id, article)
                threads.append(thread)
            return threads

    def validate_collection(self, objs, collection):
        if collection.path_level in [0, 1, 2]:
            return

    def get_thread(self, id, entry=None):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = Thread(id)
        if entry is None:
            url = id.split('#')[0]
            for article in self.browser.get_unread_feed(url):
                if article.id == id:
                    entry = article
        if entry is None:

            return None

        if thread.id not in self.storage.get('seen', default=[]):
            entry.flags = Message.IS_UNREAD

        entry.thread = thread
        thread.title = entry.title
        thread.root = entry
        return thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m

    def iter_threads(self):
        for article in self.browser.iter_threads():
            yield self.get_thread(article.id, article)

    def set_message_read(self, message):
        self.browser.set_message_read(message.thread.id.split('#')[-1])
        self.storage.get('seen', default=[]).append(message.thread.id)
        self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
            login_browser = GoogleBrowser(username, password,
                                          'https://feedly.com/v3/auth/callback&scope=profile+email&state=A8duE2XpzvtgcHt-q29qyBBK2fkpTefgqfzy7SY4GWUOPl3BgrSt4DRS-qKm9MRi_mXJRem8QW7RmNjpc_BIlkWc0JJvpay3UyzIErNvtaZLcsrUy94Ays3gTyispb8R0doguiky8gGxuCFNvJ9iXIB_SlwNhWABm7ut3nIgoMg3wodRgYOPFothhkErchrv076tBwXQA4Z8OIRyrQ')
        else:
            password = None
            login_browser = None
        return self.create_browser(username, password, login_browser)

    OBJECTS = {Thread: fill_thread}

# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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

from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.browser import BrowserForbidden
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message

from .browser import OvsBrowser


__all__ = ['OvsBackend']


class OvsBackend(BaseBackend, ICapMessages, ICapMessagesPost):
    NAME = 'ovs'
    DESCRIPTION = u'OnVaSortir website. Handles private messages only'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    VERSION = '0.h'

    CONFIG = BackendConfig(Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('city',                    label='City (subdomain)', default='paris'))
    # TODO keep list of possible cities

    BROWSER = OvsBrowser

    STORAGE = {'seen': {}}

    def create_default_browser(self):
        return self.create_browser(self.config['city'].get(),
                                   self.config['username'].get(),
                                   self.config['password'].get(),
                                   parser='raw')

    def iter_threads(self):
        with self.browser:
            for thread in self.browser.iter_threads_list():
                yield thread

    def get_thread(self, id):
        with self.browser:
            thread = self.browser.get_thread(id)

            messages = [thread.root] + thread.root.children
            for message in messages:
                if not self.storage.get('seen', message.full_id, default=False):
                    message.flags |= Message.IS_UNREAD

            return thread

    def iter_unread_messages(self):
        with self.browser:
            for thread in self.iter_threads():
                # TODO reuse thread object?
                thread2 = self.get_thread(thread.id)
                messages = [thread2.root] + thread2.root.children
                for message in messages:
                    if message.flags & Message.IS_UNREAD:
                        yield message
        # TODO implement more efficiently by having a "last weboob seen" for
        # a thread and query a thread only if "last activity" returned by web
        # is later than "last weboob seen"

    def set_message_read(self, message):
        self.storage.set('seen', message.full_id, True)
        self.storage.save()

    def post_message(self, message):
        if not self.browser.username:
            raise BrowserForbidden()

        with self.browser:
            thread = message.thread

            if message.parent:
                # ovs.<threadid>@*
                self.browser.post_to_thread(thread.id, message.title, message.content)
            else:
                # ovs.<recipient>@*
                self.browser.create_thread(thread.id, message.title, message.content)

# FIXME known bug: parsing is done in "boosted mode" which is automatically disable after some time, the "boosted mode" should be re-toggled often

# TODO support outing comments, forum messages
# TODO make an ICapOuting?


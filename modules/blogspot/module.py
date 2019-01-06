# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.messages import CapMessages, Message, Thread
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value

from .browser import BlogspotBrowser


__all__ = ['BlogspotModule']


class BlogspotModule(Module, CapMessages):
    NAME = 'blogspot'
    DESCRIPTION = u'Blog reader for blogspot. Read-only and without comments.'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    CONFIG = BackendConfig(Value('url', label='URL of the blogspot', regexp='https://[^.]+.blogspot.[^.]+/?'))

    BROWSER = BlogspotBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['url'].get())

    def get_thread(self, id):
        for thread in self.iter_threads():
            if thread.id == id:
                return thread

    def iter_threads(self):
        for msg in self.browser.iter_dates():
            thread = Thread(msg.id)
            thread.title = msg.title
            thread.date = msg.date
            thread.root = msg
            msg.thread = thread
            yield thread

    def fill_message(self, msg, fields):
        if 'content' in fields:
            assert msg._type == 'article'
            other = self.browser.get_article(msg.url)
            msg.content = other.content
            msg.sender = other.sender or NotAvailable
            msg.title = other.title or msg.title
        if 'children' in fields:
            assert msg._type == 'date'
            msg.children = list(self.browser.iter_articles(msg._key))
            for sub in msg.children:
                sub.parent = msg
                sub.thread = msg.thread

    OBJECTS = {
        Message: fill_message,
    }

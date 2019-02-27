# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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


import time
from weboob.capabilities.messages import Message, Thread
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module
from weboob.tools.newsfeed import Newsfeed

from .browser import GenericPageBrowser


class GenericNewspaperModule(Module):
    """
    GenericNewspaperModule class
    """
    NAME = u'genericnewspaper'
    MAINTAINER = u'Julien Hebert'
    DESCRIPTION = u'Generic module that helps to handle newspapers modules'
    EMAIL = 'juke@free.fr'
    VERSION = '1.6'
    LICENSE = 'AGPLv3+'
    STORAGE = {'seen': {}}
    RSS_FEED = None
    RSSID = None
    URL2ID = None
    RSSSIZE = 0
    BROWSER = GenericPageBrowser

    def create_default_browser(self):
        return self.create_browser(weboob=self.weboob)

    def get_thread(self, _id):
        if isinstance(_id, Thread):
            thread = _id
            id = thread.id
        else:
            thread = find_object(self.iter_threads(), id=_id)
            id = _id

        content = self.browser.get_content(id)

        if content is None:
            return None

        if not thread:
            thread = Thread(id)

        flags = Message.IS_HTML
        if thread.id not in self.storage.get('seen', default={}):
            flags |= Message.IS_UNREAD
        thread.title = content.title
        if not thread.date:
            thread.date = content.date

        thread.root = Message(
            thread=thread,
            id=0,
            url=content.url,
            title=content.title,
            sender=content.author,
            receivers=None,
            date=thread.date,
            parent=None,
            content=content.body,
            signature=u'<a href="%s">URL</a> \n' % content.url,
            flags=flags,
            children=[])
        return thread

    def iter_threads(self):
        for article in Newsfeed(self.RSS_FEED, GenericNewspaperModule.RSSID).iter_entries():
            thread = Thread(article.id)
            thread.title = article.title
            thread.date = article.datetime
            yield(thread)

    def fill_thread(self, thread, fields):
        "fill the thread"
        t = self.get_thread(thread)
        return t or thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            if thread.id in self.storage.get('seen', default={}):
                continue
            self.fill_thread(thread, 'root')
            for msg in thread.iter_all_messages():
                yield msg

    def set_message_read(self, message):
        self.storage.set(
            'seen',
            message.thread.id,
            'comments',
            self.storage.get(
                'seen',
                message.thread.id,
                'comments',
                default=[]) + [message.id])

        if self.URL2ID and self.RSSSIZE != 0:
            url2id = self.URL2ID
            lastpurge = self.storage.get('lastpurge', default=0)
            l = []
            if time.time() - lastpurge > 7200:
                self.storage.set('lastpurge', time.time())
                for id in self.storage.get('seen', default={}):
                    l.append((int(url2id(id)), id))
                l.sort()
                l.reverse()
                tosave = [v[1] for v in l[0:self.RSSSIZE + 10]]
                toremove = set([v for v in self.storage.get('seen', default={})]).difference(tosave)
                for id in toremove:
                    self.storage.delete('seen', id)

        self.storage.save()

    OBJECTS = {Thread: fill_thread}

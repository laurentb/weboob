# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

from __future__ import with_statement

from weboob.tools.backend import BaseBackend
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread

from .feeds import ArticlesList
from .browser import DLFP


__all__ = ['DLFPBackend']


class DLFPBackend(BaseBackend, ICapMessages, ICapMessagesPost):
    NAME = 'dlfp'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = "Da Linux French Page"
    CONFIG = {'username':      BaseBackend.ConfigField(description='Username on website', regexp='.+'),
              'password':      BaseBackend.ConfigField(description='Password of account', regexp='.+', is_masked=True),
              'get_news':      BaseBackend.ConfigField(default=True, description='Get newspapers'),
              'get_telegrams': BaseBackend.ConfigField(default=False, description='Get telegrams'),
             }
    STORAGE = {'seen': {}}
    BROWSER = DLFP

    def create_default_browser(self):
        return self.create_browser(self.config['username'], self.config['password'])

    def iter_threads(self):
        whats = set()
        if self.config['get_news']:
            whats.add('newspaper')
        if self.config['get_telegrams']:
            whats.add('telegram')

        for what in whats:
            for article in ArticlesList(what).iter_articles():
                thread = Thread(article.id)
                thread.title = article.title
                yield thread

    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id

        with self.browser:
            content = self.browser.get_content(id)

        if not thread:
            thread = Thread(id)

        flags = Message.IS_HTML
        if not thread.id in self.storage.get('seen', default={}):
            flags |= Message.IS_UNREAD

        thread.title = content.title
        if not thread.date:
            thread.date = content.date

        thread.root = Message(thread=thread,
                              id=0, # root message
                              title=content.title,
                              sender=content.author,
                              receiver=None,
                              date=thread.date, #TODO XXX WTF this is None
                              parent=None,
                              content=''.join([content.body, content.part2]),
                              signature='URL: %s' % content.url,
                              children=[],
                              flags=flags)

        for com in content.comments:
            self._insert_comment(com, thread.root)

        return thread

    def _insert_comment(self, com, parent):
        """"
        Insert 'com' comment and its children in the parent message.
        """
        flags = Message.IS_HTML
        if not com.id in self.storage.get('seen', parent.thread.id, 'comments', default=[]):
            flags |= Message.IS_UNREAD

        message = Message(thread=parent.thread,
                          id=com.id,
                          title=com.title,
                          sender=com.author,
                          receiver=None,
                          date=com.date,
                          parent=parent,
                          content=com.body,
                          signature='Score: %d' % com.score,
                          children=[],
                          flags=flags)

        parent.children.append(message)
        for sub in com.comments:
            self._insert_comment(sub, message)

    def iter_unread_messages(self, thread=None):
        for thread in self.iter_threads():
            self.fill_thread(thread, 'root')
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m

    def set_message_read(self, message):
        self.storage.set('seen', message.thread.id, 'comments', self.storage.get('seen', message.thread.id, 'comments', default=[]) + [message.id])
        self.storage.save()

    def post_mesage(self, message):
        with self.browser:
            return self.browser.post_reply(message.thread.id, message.parent.id, message.title, message.content)

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    OBJECTS = {Thread: fill_thread}

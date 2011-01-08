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
from weboob.tools.newsfeed import Newsfeed
from weboob.tools.value import Value, ValueBool, ValuesDict
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread, CantSendMessage

from .browser import DLFP
from .tools import url2id


__all__ = ['DLFPBackend']


class DLFPBackend(BaseBackend, ICapMessages, ICapMessagesPost):
    NAME = 'dlfp'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.6'
    LICENSE = 'GPLv3'
    DESCRIPTION = "Da Linux French Page"
    CONFIG = ValuesDict(Value('username',          label='Username', regexp='.+'),
                        Value('password',          label='Password', regexp='.+', masked=True),
                        ValueBool('get_news',      label='Get newspapers', default=True),
                        ValueBool('get_telegrams', label='Get telegrams', default=False))
    STORAGE = {'seen': {}}
    BROWSER = DLFP
    RSS_TELEGRAMS= "https://linuxfr.org/backend/journaux/rss20.rss"
    RSS_NEWSPAPERS = "https://linuxfr.org/backend/news/rss20.rss"


    def create_default_browser(self):
        return self.create_browser(self.config['username'], self.config['password'])

    def deinit(self):
        # don't need to logout if the browser hasn't been used.
        if not self._browser:
            return

        with self.browser:
            self.browser.close_session()

    def iter_threads(self):
        whats = set()
        if self.config['get_news']:
            whats.add(self.RSS_NEWSPAPERS)
        if self.config['get_telegrams']:
            whats.add(self.RSS_TELEGRAMS)


        for what in whats:
            for article in Newsfeed(what, url2id).iter_entries():
                thread = Thread(article.id)
                thread.title = article.title
                if article.datetime:
                    thread.date = article.datetime
                yield thread

    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = None

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
                              sender=content.author or u'',
                              receivers=None,
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
                          sender=com.author or u'',
                          receivers=None,
                          date=com.date,
                          parent=parent,
                          content=com.body,
                          signature='<br />'.join(['Score: %d' % com.score,
                                                   'URL: %s' % com.url]),
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
        self.storage.set('seen', message.thread.id, 'comments',
            self.storage.get('seen', message.thread.id, 'comments', default=[]) + [message.id])
        self.storage.save()

    def post_message(self, message):
        if not message.parent:
            raise CantSendMessage('Posting news and telegrams on DLFP is not supported yet')

        assert message.thread

        with self.browser:
            return self.browser.post_reply(message.thread.id,
                                           message.parent.id,
                                           message.title,
                                           message.content,
                                           message.flags & message.IS_HTML)

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    OBJECTS = {Thread: fill_thread}

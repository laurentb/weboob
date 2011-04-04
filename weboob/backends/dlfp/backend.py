# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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
from weboob.tools.misc import limit
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread, CantSendMessage
from weboob.capabilities.content import ICapContent, Content

from .browser import DLFP
from .tools import rssid, id2url


__all__ = ['DLFPBackend']


class DLFPBackend(BaseBackend, ICapMessages, ICapMessagesPost, ICapContent):
    NAME = 'dlfp'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.8'
    LICENSE = 'GPLv3'
    DESCRIPTION = "Da Linux French Page"
    CONFIG = ValuesDict(Value('username',          label='Username', regexp='.+'),
                        Value('password',          label='Password', regexp='.+', masked=True),
                        ValueBool('get_news',      label='Get newspapers', default=True),
                        ValueBool('get_diaries',   label='Get diaries', default=False),
                        ValueBool('get_polls',     label='Get polls', default=False),
                        ValueBool('get_board',     label='Get board', default=False),
                        ValueBool('get_wiki',      label='Get wiki', default=False),
                        ValueBool('get_tracker',   label='Get tracker', default=False))
    STORAGE = {'seen': {}}
    BROWSER = DLFP

    FEEDS = {'get_news':     "https://linuxfr.org/news.atom",
             'get_diaries':  "https://linuxfr.org/journaux.atom",
             'get_polls':    "https://linuxfr.org/sondages.atom",
             'get_board':    "https://linuxfr.org/forums.atom",
             'get_wiki':     "https://linuxfr.org/wiki.atom",
             'get_tracker':  "https://linuxfr.org/suivi.atom",
            }

    def create_default_browser(self):
        return self.create_browser(self.config['username'], self.config['password'])

    def deinit(self):
        # don't need to logout if the browser hasn't been used.
        if not self._browser:
            return

        with self.browser:
            self.browser.close_session()

    #### ICapMessages ##############################################

    def iter_threads(self):
        whats = set()
        for param, url in self.FEEDS.iteritems():
            if self.config[param]:
                whats.add(url)

        for what in whats:
            for article in limit(Newsfeed(what, rssid).iter_entries(), 20):
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

        if not content:
            return None

        if not thread:
            thread = Thread(content.id)

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
                              date=thread.date,
                              parent=None,
                              content=content.body,
                              signature='URL: %s' % self.browser.absurl(id2url(content.id)),
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
                          signature=com.signature + \
                                    '<br />'.join(['Score: %d' % com.score,
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

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    #### ICapMessagesReply #########################################
    def post_message(self, message):
        if not message.parent:
            raise CantSendMessage('Posting news and diaries on DLFP is not supported yet')

        assert message.thread

        with self.browser:
            return self.browser.post_comment(message.thread.id,
                                             message.parent.id,
                                             message.title,
                                             message.content)

    #### ICapContent ###############################################
    def get_content(self, id):
        if isinstance(id, basestring):
            content = Content(id)
        else:
            content = id
            id = content.id

        with self.browser:
            data = self.browser.get_wiki_content(id)

        if data is None:
            return None

        content.content = data
        return content

    def push_content(self, content, message=None, minor=False):
        with self.browser:
            return self.browser.set_wiki_content(content.id, content.content, message)

    def get_content_preview(self, content):
        with self.browser:
            return self.browser.get_wiki_preview(content.id, content.content)

    OBJECTS = {Thread: fill_thread}

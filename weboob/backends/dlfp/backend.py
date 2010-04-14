# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backend import Backend
from weboob.capabilities.messages import ICapMessages, ICapMessagesReply, Message

from .feeds import ArticlesList
from .browser import DLFP

class DLFPBackend(Backend, ICapMessages, ICapMessagesReply):
    NAME = 'dlfp'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '1.0'
    LICENSE = 'GPLv3'
    DESCRIPTION = "Da Linux French Page"

    CONFIG = {'username':      Backend.ConfigField(description='Username on website'),
              'password':      Backend.ConfigField(description='Password of account', is_masked=True),
              'get_news':      Backend.ConfigField(default=True, description='Get newspapers'),
              'get_telegrams': Backend.ConfigField(default=False, description='Get telegrams'),
             }
    STORAGE = {'seen': {}}
    _browser = None

    def __getattr__(self, name):
        if name == 'browser':
            if not self._browser:
                self._browser = DLFP(self.config['username'], self.config['password'])
            return self._browser
        raise AttributeError, name

    def iter_messages(self, thread=None):
        return self._iter_messages(thread, False)

    def iter_new_messages(self, thread=None):
        return self._iter_messages(thread, True)

    def _iter_messages(self, thread, only_new):
        if self.config['get_news']:
            for message in self._iter_messages_of('newspaper', thread, only_new):
                yield message
        if self.config['get_telegrams']:
            for message in self._iter_messages_of('telegram', thread, only_new):
                yield message

    def _iter_messages_of(self, what, thread_wanted, only_new):
        if not what in self.storage.get('seen', default={}):
            self.storage.set('seen', what, {})

        seen = {}
        for article in ArticlesList(what).iter_articles():
            if thread_wanted and thread_wanted != article.id:
                continue

            thread = self.browser.get_content(article.id)

            if not article.id in self.storage.get('seen', what, default={}):
                seen[article.id] = {'comments': []}
                new = True
            else:
                seen[article.id] = self.storage.get('seen', what, article.id, default={})
                new = False
            if not only_new or new:
                yield Message(thread.id,
                              0,
                              thread.title,
                              thread.author,
                              article.datetime,
                              content=''.join([thread.body, thread.part2]),
                              signature='URL: %s' % article.url,
                              is_html=True)

            for comment in thread.iter_all_comments():
                if not comment.id in seen[article.id]['comments']:
                    seen[article.id]['comments'].append(comment.id)
                    new = True
                else:
                    new = False
                if not only_new or new:
                    yield Message(thread.id,
                                  comment.id,
                                  comment.title,
                                  comment.author,
                                  comment.date,
                                  comment.reply_id,
                                  comment.body,
                                  'Score: %d' % comment.score,
                                  is_html=True)
        self.storage.set('seen', what, seen)
        self.storage.save()

    def post_reply(self, thread_id, reply_id, title, message):
        return self.browser.post(thread_id, reply_id, title, message)

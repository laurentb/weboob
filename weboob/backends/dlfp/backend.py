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
from weboob.capabilities.updatable import ICapUpdatable

from .feeds import ArticlesList
from .browser import DLFP

class DLFPBackend(Backend, ICapMessages, ICapMessagesReply, ICapUpdatable):
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
    STORAGE = {'seen': {'contents': [], 'comments': []}}
    browser = None

    def need_browser(func):
        def inner(self, *args, **kwargs):
            if not self.browser:
                self.browser = DLFP(self.config['username'], self.config['password'])

            return func(self, *args, **kwargs)
        return inner

    @need_browser
    def iter_messages(self):
        if self.config['get_news']:
            for message in self._iter_messages('newspaper'):
                yield message
        if self.config['get_telegrams']:
            for message in self._iter_messages('telegram'):
                yield message

    def _iter_messages(self, what):
        for article in ArticlesList(what).iter_articles():
            thread = self.browser.get_content(article.id)
            if not thread.id in self.storage.get(self.name, 'seen', 'contents'):
                self.storage.get(self.name, 'seen', 'contents').append(thread.id)
                yield Message(thread.id,
                              0,
                              thread.title,
                              thread.author,
                              article.datetime,
                              content=''.join([thread.body, thread.part2]),
                              signature='URL: %s' % article.url)
            for comment in thread.iter_all_comments():
                if not comment.id in self.storage.get(self.name, 'seen', 'comments'):
                    self.storage.get(self.name, 'seen', 'comments').append(comment.id)
                    yield Message(thread.id,
                                  comment.id,
                                  comment.title,
                                  comment.author,
                                  comment.date,
                                  comment.reply_id,
                                  comment.body,
                                  'Score: %d' % comment.score)
            self.storage.save(self.name)

    def iter_new_messages(self):
        return self.iter_messages()

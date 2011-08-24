# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from __future__ import with_statement

from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.newsfeed import Newsfeed
from weboob.tools.value import Value, ValueInt, ValueBackendPassword
from weboob.tools.misc import limit
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread, CantSendMessage

from .browser import PhpBB
from .tools import rssid, url2id


__all__ = ['PhpBBBackend']


class PhpBBBackend(BaseBackend, ICapMessages):
    NAME = 'phpbb'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.9'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = "phpBB forum"
    CONFIG = BackendConfig(Value('url',                     label='URL of forum', regexp='https?://.*'),
                           Value('username',                label='Username'),
                           ValueBackendPassword('password', label='Password'),
                           ValueInt('thread_unread_messages', label='Limit number of unread messages to retrieve for a thread', default=500)
                          )
    STORAGE = {'seen': {}}
    BROWSER = PhpBB

    def create_default_browser(self):
        return self.create_browser(self.config['url'].get(),
                                   self.config['username'].get(),
                                   self.config['password'].get())

    #### ICapMessages ##############################################

    def _iter_threads(self, root_link=None):
        with self.browser:
            links = list(self.browser.iter_links(root_link.url if root_link else None))

        for link in links:
            if link.type == link.FORUM:
                link.title = '%s[%s]' % (root_link.title if root_link else '', link.title)
                for thread in self._iter_threads(link):
                    yield thread
            if link.type == link.TOPIC:
                thread = Thread(url2id(link.url))
                thread.title = ('%s ' % root_link.title if root_link else '') + link.title
                thread.date = link.date
                thread.nb_messages = link.nb_messages
                thread.flags = thread.IS_DISCUSSION
                yield thread

    def iter_threads(self):
        return self._iter_threads()

    def get_thread(self, id):
        thread = None
        parent = None

        if isinstance(id, Thread):
            thread = id
            id = thread.id

        thread_id = url2id(id) or id
        try:
            last_seen_id = self.storage.get('seen', default={})[url2id(thread_id)]
        except KeyError:
            last_seen_id = 0

        with self.browser:
            for post in self.browser.iter_posts(id):
                if not thread:
                    thread = Thread(thread_id)
                    thread.title = post.title

                flags = Message.IS_HTML
                if last_seen_id < post.id:
                    flags |= Message.IS_UNREAD

                m = Message(thread=thread,
                            id=post.id,
                            title=post.title,
                            sender=post.author,
                            receivers=None,
                            date=post.date,
                            parent=parent,
                            content=post.content,
                            signature=post.signature,
                            children=[],
                            flags=flags)

                if parent:
                    parent.children = [m]
                else:
                    thread.root = m

                parent = m

        return thread

    def iter_unread_messages(self, thread=None):
        with self.browser:
            url = self.browser.get_root_feed_url()
            for article in Newsfeed(url, rssid).iter_entries():
                id = url2id(article.link)
                thread_id, message_id = [int(v) for v in id.split('.')]
                thread = Thread(thread_id)

                try:
                    last_seen_id = self.storage.get('seen', default={})[thread.id]
                except KeyError:
                    last_seen_id = 0

                child = None
                iterator = self.browser.riter_posts(id, last_seen_id)
                if self.config['thread_unread_messages'].get() > 0:
                    iterator = limit(iterator, self.config['thread_unread_messages'].get())
                for post in iterator:
                    message = Message(thread=thread,
                                      id=post.id,
                                      title=post.title,
                                      sender=post.author,
                                      receivers=None,
                                      date=post.date,
                                      parent=None,
                                      content=post.content,
                                      signature=post.signature,
                                      children=[],
                                      flags=Message.IS_UNREAD|Message.IS_HTML)
                    if child:
                        message.children.append(child)
                        child.parent = message

                    if post.parent:
                        message.parent = Message(thread=thread,
                                                 id=post.parent)
                    else:
                        thread.root = message
                    yield message

    def set_message_read(self, message):
        try:
            last_seen_id = self.storage.get('seen', default={})[message.thread.id]
        except KeyError:
            last_seen_id = 0

        if message.id > last_seen_id:
            self.storage.set('seen', int(message.thread.id), message.id)
            self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    #### ICapMessagesReply #########################################
    #def post_message(self, message):
    #    assert message.thread

    #    with self.browser:
    #        return self.browser.post_comment(message.thread.id,
    #                                         message.parent.id,
    #                                         message.title,
    #                                         message.content)

    OBJECTS = {Thread: fill_thread}

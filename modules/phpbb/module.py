# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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


from weboob.capabilities.messages import CantSendMessage, CapMessages, CapMessagesPost, Message, Thread
from weboob.tools.backend import BackendConfig, Module
from weboob.tools.misc import limit
from weboob.tools.newsfeed import Newsfeed
from weboob.tools.value import Value, ValueBackendPassword, ValueInt

from .browser import PhpBB
from .tools import id2topic, id2url, rssid, url2id

__all__ = ['PhpBBModule']


class PhpBBModule(Module, CapMessages, CapMessagesPost):
    NAME = 'phpbb'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = "phpBB forum"
    CONFIG = BackendConfig(Value('url',                     label='URL of forum', regexp='https?://.*'),
                           Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           ValueInt('thread_unread_messages', label='Limit number of unread messages to retrieve for a thread', default=500)
                           )
    STORAGE = {'seen': {}}
    BROWSER = PhpBB

    def create_default_browser(self):
        username = self.config['username'].get()
        if len(username) > 0:
            password = self.config['password'].get()
        else:
            password = None
        return self.create_browser(self.config['url'].get(),
                                   username, password)

    #### CapMessages ##############################################

    def _iter_threads(self, root_link=None):
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

        thread_id = url2id(id, nopost=True) or id
        try:
            last_seen_id = self.storage.get('seen', default={})[id2topic(thread_id)]
        except KeyError:
            last_seen_id = 0

        for post in self.browser.iter_posts(id):
            if not thread:
                thread = Thread(thread_id)
                thread.title = post.title

            m = self._post2message(thread, post)
            m.parent = parent
            if last_seen_id < post.id:
                m.flags |= Message.IS_UNREAD

            if parent:
                parent.children = [m]
            else:
                thread.root = m

            parent = m

        return thread

    def _post2message(self, thread, post):
        signature = post.signature
        if signature:
            signature += '<br />'
        signature += 'URL: %s' % self.browser.absurl(id2url('%s.%s' % (thread.id, post.id)))
        return Message(thread=thread,
                       id=post.id,
                       title=post.title,
                       sender=post.author,
                       receivers=None,
                       date=post.date,
                       parent=None,
                       content=post.content,
                       signature=signature,
                       children=[],
                       flags=Message.IS_HTML)

    def iter_unread_messages(self):
        url = self.browser.get_root_feed_url()
        for article in Newsfeed(url, rssid).iter_entries():
            id = url2id(article.link)
            thread = None

            try:
                last_seen_id = self.storage.get('seen', default={})[id2topic(id)]
            except KeyError:
                last_seen_id = 0

            child = None
            iterator = self.browser.riter_posts(id, last_seen_id)
            if self.config['thread_unread_messages'].get() > 0:
                iterator = limit(iterator, self.config['thread_unread_messages'].get())
            for post in iterator:
                if not thread:
                    thread = Thread('%s.%s' % (post.forum_id, post.topic_id))
                message = self._post2message(thread, post)

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
            last_seen_id = self.storage.get('seen', default={})[id2topic(message.thread.id)]
        except KeyError:
            last_seen_id = 0

        if message.id > last_seen_id:
            self.storage.set('seen', id2topic(message.thread.id), message.id)
            self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    #### CapMessagesReply #########################################
    def post_message(self, message):
        assert message.thread

        forum = 0
        topic = 0
        if message.thread:
            try:
                if '.' in message.thread.id:
                    forum, topic = [int(i) for i in message.thread.id.split('.', 1)]
                else:
                    forum = int(message.thread.id)
            except ValueError:
                raise CantSendMessage('Thread ID must be in form "FORUM_ID[.TOPIC_ID]".')

        return self.browser.post_answer(forum,
                                        topic,
                                        message.title,
                                        message.content)

    OBJECTS = {Thread: fill_thread}

# -*- coding: utf-8 -*-

# Copyright(C) 2011  Julien Hebert
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
"backend for http://20minutes.fr"

# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.messages import ICapMessages, Message, Thread
from weboob.tools.backend import BaseBackend

from .browser import Newspaper20minutesBrowser
from weboob.tools.newsfeed import Newsfeed
from .tools import url2id

__all__ = ['Newspaper20minutesBackend']




class Newspaper20minutesBackend(BaseBackend, ICapMessages):
    NAME = 'minutes20'
    MAINTAINER = 'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.6'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'20minutes French news  website'
    #CONFIG = ValuesDict(Value('login',      label='Account ID'),
    #                    Value('password',   label='Password', masked=True))
    STORAGE = {'seen': {}}
    BROWSER = Newspaper20minutesBrowser

    def get_thread(self, _id):
        if isinstance(_id, Thread):
            thread = _id
            _id = thread.id
        else:
            thread = None

        with self.browser:
            content = self.browser.get_content(_id)

        if not thread:
            thread = Thread(_id)


        flags = Message.IS_HTML
        if not thread.id in self.storage.get('seen', default={}):
            flags |= Message.IS_UNREAD
        thread.title = content.title
        if not thread.date:
            thread.date = content.date

        thread.root = Message(
            thread=thread,
            id=0,
            title=content.title,
            sender=content.author,
            receivers=None,
            date=thread.date,
            parent=None,
            content=content.body,
            flags=flags,
            children= [])
        return thread

    def iter_threads(self):
        for article in Newsfeed('http://www.20minutes.fr/rss/20minutes.xml', 
            url2id).iter_entries():
            thread = Thread(article.id)
            thread.title =  article.title
            thread.date = article.datetime
            yield(thread)

    def fill_thread(self, thread):
        return self.get_thread(thread)

    def iter_unread_messages(self, thread=None):
        for thread in self.iter_threads():
            self.fill_thread(thread)
            for msg in thread.iter_all_messages():
                if msg.flags & msg.IS_UNREAD:
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
        self.storage.save()

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


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.messages import ICapMessages, Message, Thread
from weboob.tools.backend import BaseBackend

from .browser import Newspaper20minutesBrowser
from weboob.tools.newsfeed import Newsfeed


__all__ = ['Newspaper20minutesBackend']


class Newspaper20minutesBackend(BaseBackend, ICapMessages):
    NAME = 'minutes20'
    MAINTAINER = 'Julien Hebert'
    EMAIL = 'juke@free.fr'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'20minutes French news  website'
    #CONFIG = ValuesDict(Value('login',      label='Account ID'),
    #                    Value('password',   label='Password', masked=True))
    BROWSER = Newspaper20minutesBrowser

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

        thread.title = content.title
        if not thread.date:
            thread.date = content.date

        #thread.root = Message(thread=thread, id=0, title=content.title, sender=content.author, receivers=None, date=thread.date, parent=None, content=content.body, signature=None, children = [], flags=flags)

        thread.root = Message(thread=thread, id=0, title=content.title, sender=content.author, receivers=None, date=thread.date, parent=None, content=content.body)
        return thread

    def set_message_read(self, message):
        raise NotImplementedError()
    
    def iter_threads(self):
        for article in Newsfeed('http://www.20minutes.fr/rss/une.xml').iter_entries():
            thread = Thread(article.id)
            thread.title =  article.title
            thread.date = article.datetime
            yield(thread)

    def iter_unread_messages(self, thread=None):
        for thread in self.iter_threads():
            self.fill_thread(thread, 'root')
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m

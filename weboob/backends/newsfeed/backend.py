# -*- coding: utf-8 -*-

# Copyright(C) 2010  Clément Schreiner
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


from weboob.tools.backend import BaseBackend
from weboob.capabilities.messages import ICapMessages, Message, Thread
from weboob.tools.newsfeed import Newsfeed
from weboob.tools.value import Value, ValuesDict


__all__ = ['NewsfeedBackend']


class NewsfeedBackend(BaseBackend, ICapMessages):
    NAME = 'newsfeed'
    MAINTAINER = u"Clément Schreiner"
    EMAIL = "clemux@clemux.info"
    VERSION = '0.4'
    DESCRIPTION = "Loads RSS and Atom feeds from any websites"
    LICENSE = "GPLv3"
    CONFIG = ValuesDict(Value('url', label="Atom/RSS feed's url"))
    STORAGE = {'seen': []}


    def iter_threads(self):
        for article in Newsfeed(self.config["url"]).iter_entries():
            thread = Thread(article.id)
            thread.title = article.title
            yield thread



    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = Thread(id)
        entry = Newsfeed(self.config["url"]).get_entry(id)
        flags = Message.IS_HTML
        if not thread.id in self.storage.get('seen', default=[]):
            flags |= Message.IS_UNREAD
        if len(entry.content):
            content = entry.content[0]
        else:
            content = None
        thread.title = entry.title
        thread.root = Message(thread=thread,
                              id=0,
                              title=entry.title,
                              sender=entry.author,
                              receiver=None,
                              date=entry.datetime,
                              parent=None,
                              content=content,
                              children=[],
                              flags=flags)
        return thread



    def iter_unread_messages(self, thread=None):
        for thread in self.iter_threads():
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m


    def set_message_read(self, message):
        self.storage.get('seen', default=[]).append(message.thread.id)
        self.storage.save()

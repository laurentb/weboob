# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Clément Schreiner
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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.messages import CapMessages, Message, Thread
from weboob.tools.newsfeed import Newsfeed
from weboob.tools.value import Value


__all__ = ['NewsfeedModule']


class NewsfeedModule(Module, CapMessages):
    NAME = 'newsfeed'
    MAINTAINER = u'Clément Schreiner'
    EMAIL = "clemux@clemux.info"
    VERSION = '1.5'
    DESCRIPTION = "Loads RSS and Atom feeds from any website"
    LICENSE = "AGPLv3+"
    CONFIG = BackendConfig(Value('url', label="Atom/RSS feed's url", regexp='https?://.*'))
    STORAGE = {'seen': []}

    def iter_threads(self):
        for article in Newsfeed(self.config['url'].get()).iter_entries():
            yield self.get_thread(article.id, article)

    def get_thread(self, id, entry=None):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = Thread(id)

        if entry is None:
            entry = Newsfeed(self.config['url'].get()).get_entry(id)
        if entry is None:
            return None

        flags = Message.IS_HTML
        if thread.id not in self.storage.get('seen', default=[]):
            flags |= Message.IS_UNREAD
        if len(entry.content) > 0:
            content = u"<p>Link %s</p> %s" % (entry.link, entry.content[0])
        else:
            content = entry.link

        thread.title = entry.title
        thread.root = Message(thread=thread,
                              id=0,
                              url=entry.link,
                              title=entry.title,
                              sender=entry.author,
                              receivers=None,
                              date=entry.datetime,
                              parent=None,
                              content=content,
                              children=[],
                              flags=flags)
        return thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            for m in thread.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m

    def set_message_read(self, message):
        self.storage.get('seen', default=[]).append(message.thread.id)
        self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    OBJECTS = {Thread: fill_thread}

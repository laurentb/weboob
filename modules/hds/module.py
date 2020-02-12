# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from weboob.tools.backend import Module
from weboob.capabilities.messages import CapMessages, Message, Thread

from .browser import HDSBrowser


__all__ = ['HDSModule']


class HDSModule(Module, CapMessages):
    NAME = 'hds'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.0'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Histoires de Sexe French erotic novels"
    STORAGE = {'seen': []}
    BROWSER = HDSBrowser

    #### CapMessages ##############################################

    def iter_threads(self):
        for story in self.browser.iter_stories():
            thread = Thread(story.id)
            thread.title = story.title
            thread.date = story.date
            yield thread

    GENDERS = ['<unknown>', 'boy', 'girl', 'transexual']

    def get_thread(self, id):
        if isinstance(id, Thread):
            thread = id
            id = thread.id
        else:
            thread = None

        story = self.browser.get_story(id)

        if not story:
            return None

        if not thread:
            thread = Thread(story.id)

        flags = 0
        if thread.id not in self.storage.get('seen', default=[]):
            flags |= Message.IS_UNREAD

        thread.title = story.title
        thread.date = story.date
        thread.root = Message(thread=thread,
                              id=0,
                              title=story.title,
                              sender=story.author.name,
                              receivers=None,
                              date=thread.date,
                              parent=None,
                              content=story.body,
                              children=[],
                              signature=u'Written by a %s in category %s' % (self.GENDERS[story.author.sex], story.category),
                              flags=flags)

        return thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            if thread.id in self.storage.get('seen', default=[]):
                continue
            self.fill_thread(thread, 'root')
            yield thread.root

    def set_message_read(self, message):
        self.storage.set('seen', self.storage.get('seen', default=[]) + [message.thread.id])
        self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    OBJECTS = {Thread: fill_thread}

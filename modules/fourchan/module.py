# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.capabilities.messages import CapMessages, Message, Thread
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value

from .browser import FourChan


__all__ = ['FourChanModule']


class FourChanModule(Module, CapMessages):
    NAME = 'fourchan'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = '4chan image board'
    CONFIG = BackendConfig(Value('boards', label='Boards to fetch'))
    STORAGE = {'boards': {}}
    BROWSER = FourChan

    def _splitid(self, id):
        return id.split('.', 1)

    def get_thread(self, id):
        thread = None

        if isinstance(id, Thread):
            thread = id
            id = thread.id

        if '.' not in id:
            self.logger.warning('Malformated ID (%s)' % id)
            return

        board, thread_id = self._splitid(id)

        with self.browser:
            _thread = self.browser.get_thread(board, thread_id)

        flags = 0
        if _thread.id not in self.storage.get('boards', board, default={}):
            flags |= Message.IS_UNREAD

        if not thread:
            thread = Thread(id)
        thread.title = _thread.filename
        thread.root = Message(thread=thread,
                              id=0,  # root message
                              title=_thread.filename,
                              sender=_thread.author,
                              receivers=None,
                              date=_thread.datetime,
                              parent=None,
                              content=_thread.text,
                              signature=None,
                              children=[],
                              flags=flags|Message.IS_HTML)

        for comment in _thread.comments:
            flags = 0
            if comment.id not in self.storage.get('boards', board, _thread.id, default=[]):
                flags |= Message.IS_UNREAD

            m = Message(thread=thread,
                        id=comment.id,
                        title=_thread.filename,
                        sender=comment.author,
                        receivers=None,
                        date=comment.datetime,
                        parent=thread.root,
                        content=comment.text,
                        signature=None,
                        children=None,
                        flags=flags|Message.IS_HTML)
            thread.root.children.append(m)

        return thread

    def iter_threads(self):
        for board in self.config['boards'].get().split(' '):
            with self.browser:
                threads = self.browser.get_threads(board)
            for thread in threads:
                t = Thread('%s.%s' % (board, thread.id))
                t.title = thread.filename
                yield t

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            self.fill_thread(thread, 'root')

            for m in thread.iter_all_messages():
                if m.flags & Message.IS_UNREAD:
                    yield m

    def set_message_read(self, message):
        board, thread_id = self._splitid(message.thread.id)
        self.storage.set('boards', board, thread_id, self.storage.get('boards', board, thread_id, default=[]) + [message.id])
        self.storage.save()

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    OBJECTS = {Thread: fill_thread}

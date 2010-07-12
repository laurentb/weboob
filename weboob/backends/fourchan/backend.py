# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


from __future__ import with_statement

from logging import warning

from weboob.capabilities.messages import ICapMessages, Message
from weboob.tools.backend import BaseBackend

from .browser import FourChan


__all__ = ['FourChanBackend']


class FourChanBackend(BaseBackend, ICapMessages):
    NAME = 'fourchan'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = "4chan website"

    CONFIG = {'boards': BaseBackend.ConfigField(description='Boards'),
             }
    STORAGE = {'boards': {}}
    BROWSER = FourChan

    def iter_messages(self, thread=None):
        return self._iter_messages(thread, False)

    def iter_new_messages(self, thread=None):
        return self._iter_messages(thread, True)

    def _iter_messages(self, thread, only_new):
        if thread:
            if '.' in thread:
                board, thread = thread.split('.', 2)
                return self._iter_messages_of(board, thread, only_new)
            else:
                warning('"%s" is not a valid ID' % thread)
        else:
            for board in self.config['boards'].split(' '):
                return self._iter_messages_of(board, None, only_new)

    def _iter_messages_of(self, board, thread_wanted, only_new):
        if not board in self.storage.get('boards', default={}):
            self.storage.set('boards', board, {})

        if thread_wanted:
            for message in self._iter_thread_messages(board, thread_wanted, only_new):
                yield message
        else:
            with self.browser:
                threads = self.browser.get_threads(board)
            for thread in threads:
                for message in self._iter_thread_messages(board, thread.id, only_new):
                    yield message

    def _iter_thread_messages(self, board, thread, only_new):
        thread = self.browser.get_thread(board, thread)

        if thread.id in self.storage.get('boards', board, default={}):
            self.storage.set('boards', board, thread.id, [])
            new = True
        else:
            new = False

        if not only_new or new:
            yield Message('%s.%s' % (board, thread.id),
                          0,
                          thread.filename,
                          thread.author,
                          thread.datetime,
                          content=thread.text,
                          is_html=True,
                          is_new=new)

        for comment in thread.comments:
            if not comment.id in self.storage.get('boards', board, thread.id, default=[]):
                self.storage.set('boards', board, thread.id, self.storage.get('boards', board, thread.id, default=[]) + [comment.id])
                new = True
            else:
                new = False

            if not only_new or new:
                yield Message('%s.%s' % (board, thread.id),
                              comment.id,
                              thread.filename,
                              comment.author,
                              comment.datetime,
                              0,
                              comment.text,
                              is_html=True,
                              is_new=new)

        self.storage.save()

    #def post_reply(self, thread_id, reply_id, title, message):
    #    return self.browser.post_reply(thread_id, reply_id, title, message)

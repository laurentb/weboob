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


import datetime
import time

from .base import IBaseCap, CapBaseObject, NotLoaded


__all__ = ['ICapMessages', 'ICapMessagesPost', 'Message', 'Thread', 'CantSendMessage']


class Message(CapBaseObject):
    IS_HTML = 0x001          # The content is HTML formatted
    IS_UNREAD = 0x002        # The message is unread
    IS_ACCUSED = 0x004       # The receiver has read this message
    IS_NOT_ACCUSED = 0x008   # The receiver has not read this message

    def __init__(self, thread, id,
                       title=NotLoaded,
                       sender=NotLoaded,
                       receiver=NotLoaded,
                       date=None,
                       parent=NotLoaded,
                       content=NotLoaded,
                       signature=NotLoaded,
                       children=NotLoaded,
                       flags=0):
        CapBaseObject.__init__(self, id)
        self.add_field('thread', Thread, thread)
        self.add_field('title', basestring, title)
        self.add_field('sender', basestring, sender)
        self.add_field('receiver', basestring, receiver)
        self.add_field('date', datetime.datetime, date)
        self.add_field('parent', Message, parent)
        self.add_field('content', basestring, content)
        self.add_field('signature', basestring, signature)
        self.add_field('children', list, children)
        self.add_field('flags', int, flags)

        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date

        if isinstance(parent, Message):
            self.parent = parent
        else:
            self.parent = NotLoaded
            self._parent_id = parent

    @property
    def date_int(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.date.timetuple()))

    @property
    def full_id(self):
        return '%s.%s' % (self.thread.id, self.id)

    @property
    def full_parent_id(self):
        if self.parent:
            return self.parent.full_id()
        elif self._parent_id is None:
            return ''
        elif self._parent_id is NotLoaded:
            return NotLoaded
        else:
            return '%s.%s' % (self.thread.id, self._parent_id)

    def __eq__(self, msg):
        return unicode(self.thread.id) == unicode(msg.thread.id) and \
               unicode(self.id) == unicode(msg.id)

    def __repr__(self):
        result = '<Message id="%s" title="%s" date="%s" from="%s">' % (
            self.full_id, self.title, self.date, self.sender)
        return result.encode('utf-8')

class Thread(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('root', Message)
        self.add_field('title', basestring)
        self.add_field('date', datetime.datetime)
        self.add_field('nb_messages', int)
        self.add_field('nb_unread', int)

    def iter_all_messages(self):
        if self.root:
            yield self.root
            for m in self._iter_all_messages(self.root):
                yield m

    def _iter_all_messages(self, message):
        if message.children:
            for child in message.children:
                yield child
                for m in self._iter_all_messages(child):
                    yield m

class ICapMessages(IBaseCap):
    def iter_threads(self):
        """
        Iterates on threads, from newers to olders.

        @return [iter]  Thread objects
        """
        raise NotImplementedError()

    def get_thread(self, id):
        """
        Get a specific thread.

        @return [Thread]  the Thread object
        """
        raise NotImplementedError()

    def iter_unread_messages(self, thread=None):
        """
        Iterates on messages which hasn't been marked as read.

        @param thread  thread name (optional)
        @return [iter]  Message objects
        """
        raise NotImplementedError()

    def set_message_read(self, message):
        """
        Set a message as read.

        @param [message]  message read (or ID)
        """
        raise NotImplementedError()

class CantSendMessage(Exception):
    pass

class ICapMessagesPost(IBaseCap):
    def post_message(self, message):
        """
        Post a message.

        @param message  Message object
        @return
        """
        raise NotImplementedError()

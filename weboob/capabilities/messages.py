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


__all__ = ['ICapMessages', 'ICapMessagesReply', 'Message']


class Message(CapBaseObject):
    IS_HTML = 0x001
    IS_NEW  = 0x002
    IS_UNREAD = 0x004

    def __init__(self, thread_id, message_id, title, sender, date=None, parent_message_id=u'',
                 content=u'', signature=u'', flags=0):
        CapBaseObject.__init__(self, '%s.%s' % (thread_id, message_id))

        self.thread_id = unicode(thread_id)
        self.message_id = unicode(message_id)
        self.parent_message_id = unicode(parent_message_id)
        self.title = unicode(title)
        self.sender = unicode(sender)
        self.signature = unicode(signature)

        self.content = content
        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date
        self.flags = flags

    @property
    def date_int(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.date.timetuple()))

    @property
    def parent_id(self):
        if not self.parent_message_id:
            return ''
        return '%s.%s' % (self.thread_id, self.parent_message_id)

    def __eq__(self, msg):
        return self.id == msg.id

    def __repr__(self):
        result = '<Message id="%s" title="%s" date="%s" from="%s">' % (
            self.id, self.title, self.date, self.sender)
        return result.encode('utf-8')

class ICapMessages(IBaseCap):
    def iter_new_messages(self, thread=None):
        """
        Iterates on new messages from last time this function has been called.

        @param thread  thread name (optional)
        @return [list]  Message objects
        """
        raise NotImplementedError()

    def iter_messages(self, thread=None):
        """
        Iterates on every messages

        @param thread  thread name (optional)
        @return [list]  Message objects
        """
        raise NotImplementedError()

class ICapMessagesReply(IBaseCap):
    def post_reply(self, thread_id, reply_id, title, message):
        """
        Post a reply.

        @param thread_id  ID of thread
        @param reply_id  message's id to reply
        @param title  title of message
        @param message  message to send
        """
        raise NotImplementedError()

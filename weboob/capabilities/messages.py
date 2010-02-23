# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

import datetime
import time

class Message:
    def __init__(self, thread_id, id, title, sender, date=None, reply_id=''):
        self.thread_id = unicode(thread_id)
        self.id = unicode(id)
        self.reply_id = unicode(reply_id)
        self.title = unicode(title)
        self.sender = unicode(sender)

        self.new = False
        self.content = u''
        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date

    def getDateInt(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.getDate().timetuple()))

    def getFullID(self):
        return '%s.%s' % (self.id, self.thread_id)

    def getFullReplyID(self):
        return '%s.%s' % (self.reply_id, self.thread_id)

    def getID(self):
        return self.id

    def getThreadID(self):
        return self.thread_id

    def getReplyID(self):
        return self.reply_id

    def getTitle(self):
        return self.title

    def getDate(self):
        return self.date

    def getFrom(self):
        return self.sender

    def getContent(self):
        return self.content

    def isNew(self):
        return self.new

class ICapMessages:
    def getNewMessages(self, thread=None):
        """
        Get new messages from last time this function has been called.

        @param thread [str]  if given, get new messages for a specific thread.
        @return [list]  a list of Message objects.
        """
        raise NotImplementedError()

class ICapMessagesReply:
    def postReply(self, message):
        raise NotImplementedError()

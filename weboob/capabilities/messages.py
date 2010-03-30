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
    def __init__(self, thread_id, _id, title, sender, date=None, reply_id=u'', content=u'', signature=u''):
        self.thread_id = unicode(thread_id)
        self.id = unicode(_id)
        self.reply_id = unicode(reply_id)
        self.title = unicode(title)
        self.sender = unicode(sender)
        self.signature = unicode(signature)

        self.new = False
        self.content = content
        if date is None:
            date = datetime.datetime.utcnow()
        self.date = date

    def get_date_int(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.get_date().timetuple()))

    def get_full_id(self):
        return '%s.%s' % (self.id, self.thread_id)

    def get_full_reply_id(self):
        return '%s.%s' % (self.reply_id, self.thread_id)

    def get_id(self):
        return self.id

    def get_thread_id(self):
        return self.thread_id

    def get_reply_id(self):
        return self.reply_id

    def get_title(self):
        return self.title

    def get_date(self):
        return self.date

    def get_from(self):
        return self.sender

    def get_content(self):
        return self.content

    def get_signature(self):
        return self.signature

    def is_new(self):
        return self.new

    def __eq__(self, msg):
        return self.id == msg.id and self.thread_id == msg.thread_id

    def __repr__(self):
        result = '<Message id="%s" title="%s" date="%s" from="%s">' % (
            self.id, self.title, self.date, self.sender)
        return result.encode('utf-8')

class ICapMessages:
    def iter_new_messages(self):
        """
        Iterates on new messages from last time this function has been called.

        @return [list]  Message objects
        """
        raise NotImplementedError()

    def iter_messages(self):
        """
        Iterates on every messages
        """
        raise NotImplementedError()

class ICapMessagesReply:
    def post_reply(self, to, message):
        raise NotImplementedError()

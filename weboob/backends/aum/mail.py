# -*- coding: utf-8 -*-

"""
Copyright(C) 2008  Romain Bignon

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

import time
import datetime

class Mail:

    def __init__(self, id, name):
        self.id = id
        self.reply_date = 0
        self.name = name
        self.sender = name
        self.profile_link = ''

        self.new = False
        self.content = ''
        self.date = datetime.datetime.utcnow()

    def get_date_int(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.get_date().timetuple()))

    def get_msg_id(self, sender):
        return '<%s.%d@%s>' % (self.get_date_int(), self.id, sender)

    def get_reply_id(self, sender):
        if self.reply_date:
            return '<%s.%d@%s>' % (self.reply_date, self.id, sender)
        else:
            return ''

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_date(self):
        return self.date

    def get_profile_link(self):
        return self.profile_link

    def get_from(self):
        return self.sender

    def get_content(self):
        return self.content

    def is_new(self):
        return self.new


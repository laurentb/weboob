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

    def getDateInt(self):
        return int(time.strftime('%Y%m%d%H%M%S', self.getDate().timetuple()))

    def getMsgID(self, sender):
        return '<%s.%d@%s>' % (self.getDateInt(), self.id, sender)

    def getReplyID(self, sender):
        if self.reply_date:
            return '<%s.%d@%s>' % (self.reply_date, self.id, sender)
        else:
            return ''

    def getID(self):
        return self.id

    def getName(self):
        return self.name

    def getDate(self):
        return self.date

    def getProfileLink(self):
        return self.profile_link

    def getFrom(self):
        return self.sender

    def getContent(self):
        return self.content

    def isNew(self):
        return self.new


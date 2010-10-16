# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
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

from .base import IBaseCap, CapBaseObject


__all__ = ['ChatException', 'ICapChat']


class ChatException(Exception):
    pass


class ChatMessage(CapBaseObject):
    def __init__(self, id_from, id_to, message, date=None):
        CapBaseObject.__init__(self, '%s.%s' % (id_from, id_to))
        self.add_field('id_from', basestring, id_from)
        self.add_field('id_to', basestring, id_to)
        self.add_field('message', basestring, message)
        self.add_field('date', datetime.datetime, date)

        if self.date is None:
            self.date = datetime.datetime.utcnow()


class ICapChat(IBaseCap):
    def iter_chat_messages(self, _id=None):
        raise NotImplementedError()

    def send_chat_message(self, _id, message):
        raise NotImplementedError()

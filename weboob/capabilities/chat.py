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


from .cap import ICap


__all__ = ['ChatException', 'ICapChat']


class ChatException(Exception):
    pass


class Contact(object):
    def __init__(self, _id, pseudo, online, name=None, avatar_url=None, age=None):
        self.id = _id
        self.pseudo = pseudo
        self.online = online
        self.name = name
        self.avatar_url = avatar_url
        self.age = age


class ICapChat(ICap):
    def iter_chat_contacts(self, online=True, offline=True):
        raise NotImplementedError()

    def send_chat_message(self, _id, message):
        raise NotImplementedError()

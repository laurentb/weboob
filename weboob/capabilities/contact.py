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


from .cap import ICap


__all__ = ['ICapContact', 'Contact']


class Contact(object):
    STATUS_ONLINE =  0x001
    STATUS_OFFLINE = 0x002
    STATUS_AWAY =    0x004
    STATUS_ALL =     0xfff

    def __init__(self, id, name, status, photo_url=None, thumbnail_url=None):
        self.id = id
        self.name = name
        self.status = status
        self.photo_url = photo_url
        self.thumbnail_url = thumbnail_url

    def iter_fields(self):
        return {'id': self.id,
                'name': self.name,
                'status': self.status,
                'photo_url': self.photo_url,
                'thumbnail_url': self.thumbnail_url,
               }.iteritems()

class ICapContact(ICap):
    def iter_contacts(self, status=Contact.STATUS_ALL):
        raise NotImplementedError()

    def get_contact(self, id):
        raise NotImplementedError()

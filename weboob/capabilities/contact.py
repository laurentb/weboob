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
from weboob.tools.ordereddict import OrderedDict


__all__ = ['ICapContact', 'Contact']

class ProfileNode(object):
    HEAD =    0x01
    SECTION = 0x02

    def __init__(self, name, label, value, sufix=None, flags=0):
        self.name = name
        self.label = label
        self.value = value
        self.sufix = sufix
        self.flags = flags

class ContactPhoto(object):
    def __init__(self, name):
        self.name = name
        self.url = u''
        self.data = ''
        self.thumbnail_url = u''
        self.thumbnail_data = u''

    def __iscomplete__(self):
        return (self.data and (not self.thumbnail_url or self.thumbnail_data))

    def __repr__(self):
        return u'<ContactPhoto "%s" data=%do tndata=%do>' % (self.name, len(self.data), len(self.thumbnail_data))

class Contact(object):
    STATUS_ONLINE =  0x001
    STATUS_AWAY =    0x002
    STATUS_OFFLINE = 0x004
    STATUS_ALL =     0xfff

    def __init__(self, id, name, status):
        self.id = id
        self.name = name
        self.status = status
        self.status_msg = u''
        self.summary = u''
        self.avatar = None
        self.photos = OrderedDict()
        self.profile = None

    def set_photo(self, name, **kwargs):
        if not name in self.photos:
            self.photos[name] = ContactPhoto(name)

        photo = self.photos[name]
        for key, value in kwargs.iteritems():
            setattr(photo, key, value)

    def iter_fields(self):
        return {'id': self.id,
                'name': self.name,
                'status': self.status,
                'status_msg': self.status_msg,
                'summary': self.summary,
                'avatar': self.avatar,
                'photos': self.photos,
                'profile': self.profile,
               }.iteritems()

class ICapContact(ICap):
    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        """
        Iter contacts

        @param status  get only contacts with the specified status
        @param ids  if set, get the specified contacts
        @return  iterator over the contacts found
        """
        raise NotImplementedError()

    def get_contact(self, id):
        """
        Get a contact from his id.

        The default implementation only calls iter_contacts()
        with the proper values, but it might be overloaded
        by backends.

        @param id  the ID requested
        @return  the Contact object, or None if not found
        """

        l = self.iter_contacts(ids=[id])
        try:
            return l[0]
        except IndexError:
            return None

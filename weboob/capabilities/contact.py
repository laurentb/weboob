# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.


from .base import Capability, BaseObject, Field, StringField, BytesField, IntField, \
                  UserError
from weboob.tools.ordereddict import OrderedDict


__all__ = ['ProfileNode', 'ContactPhoto', 'Contact', 'QueryError', 'Query', 'CapContact']


class ProfileNode(object):
    """
    Node of a :class:`Contact` profile.
    """
    HEAD =    0x01
    SECTION = 0x02

    def __init__(self, name, label, value, sufix=None, flags=0):
        self.name = name
        self.label = label
        self.value = value
        self.sufix = sufix
        self.flags = flags

    def __getitem__(self, key):
        return self.value[key]


class ContactPhoto(BaseObject):
    """
    Photo of a contact.
    """
    name =              StringField('Name of the photo')
    url =               StringField('Direct URL to photo')
    data =              BytesField('Data of photo')
    thumbnail_url =     StringField('Direct URL to thumbnail')
    thumbnail_data =    BytesField('Data of thumbnail')
    hidden =            Field('True if the photo is hidden on website', bool)

    def __init__(self, name):
        BaseObject.__init__(self, name)
        self.name = name

    def __iscomplete__(self):
        return (self.data and (not self.thumbnail_url or self.thumbnail_data))

    def __str__(self):
        return self.url

    def __repr__(self):
        return u'<ContactPhoto "%s" data=%do tndata=%do>' % (self.id,
                                                             len(self.data) if self.data else 0,
                                                             len(self.thumbnail_data) if self.thumbnail_data else 0)


class Contact(BaseObject):
    """
    A contact.
    """
    STATUS_ONLINE =  0x001
    STATUS_AWAY =    0x002
    STATUS_OFFLINE = 0x004
    STATUS_ALL =     0xfff

    name =          StringField('Name of contact')
    status =        IntField('Status of contact (STATUS_* constants)')
    url =           StringField('URL to the profile of contact')
    status_msg =    StringField('Message of status')
    summary =       StringField('Description of contact')
    photos =        Field('List of photos', dict, default=OrderedDict())
    profile =       Field('Contact profile', dict, default=OrderedDict())

    def __init__(self, id, name, status):
        BaseObject.__init__(self, id)
        self.name = name
        self.status = status

    def set_photo(self, name, **kwargs):
        """
        Set photo of contact.

        :param name: name of photo
        :type name: str
        :param kwargs: See :class:`ContactPhoto` to know what other parameters you can use
        """
        if name not in self.photos:
            self.photos[name] = ContactPhoto(name)

        photo = self.photos[name]
        for key, value in kwargs.iteritems():
            setattr(photo, key, value)

    def get_text(self):
        def print_node(node, level=1):
            result = u''
            if node.flags & node.SECTION:
                result += u'\t' * level + node.label + '\n'
                for sub in node.value.itervalues():
                    result += print_node(sub, level + 1)
            else:
                if isinstance(node.value, (tuple, list)):
                    value = ', '.join(unicode(v) for v in node.value)
                elif isinstance(node.value, float):
                    value = '%.2f' % node.value
                else:
                    value = node.value
                result += u'\t' * level + u'%-20s %s\n' % (node.label + ':', value)
            return result

        result = u'Nickname: %s\n' % self.name
        if self.status & Contact.STATUS_ONLINE:
            s = 'online'
        elif self.status & Contact.STATUS_OFFLINE:
            s = 'offline'
        elif self.status & Contact.STATUS_AWAY:
            s = 'away'
        else:
            s = 'unknown'
        result += u'Status: %s (%s)\n' % (s, self.status_msg)
        result += u'URL: %s\n' % self.url
        result += u'Photos:\n'
        for name, photo in self.photos.iteritems():
            result += u'\t%s%s\n' % (photo, ' (hidden)' if photo.hidden else '')
        result += u'\nProfile:\n'
        for head in self.profile.itervalues():
            result += print_node(head)
        result += u'Description:\n'
        for s in self.summary.split('\n'):
            result += u'\t%s\n' % s
        return result


class QueryError(UserError):
    """
    Raised when unable to send a query to a contact.
    """


class Query(BaseObject):
    """
    Query to send to a contact.
    """
    message =   StringField('Message received')

    def __init__(self, id, message):
        BaseObject.__init__(self, id)
        self.message = message


class CapContact(Capability):
    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        """
        Iter contacts

        :param status: get only contacts with the specified status
        :type status: Contact.STATUS_*
        :param ids: if set, get the specified contacts
        :type ids: list[str]
        :rtype: iter[:class:`Contact`]
        """
        raise NotImplementedError()

    def get_contact(self, id):
        """
        Get a contact from his id.

        The default implementation only calls iter_contacts()
        with the proper values, but it might be overloaded
        by backends.

        :param id: the ID requested
        :type id: str
        :rtype: :class:`Contact` or None if not found
        """

        l = self.iter_contacts(ids=[id])
        try:
            return l[0]
        except IndexError:
            return None

    def send_query(self, id):
        """
        Send a query to a contact

        :param id: the ID of contact
        :type id: str
        :rtype: :class:`Query`
        :raises: :class:`QueryError`
        """
        raise NotImplementedError()

    def get_notes(self, id):
        """
        Get personal notes about a contact

        :param id: the ID of the contact
        :type id: str
        :rtype: unicode
        """
        raise NotImplementedError()

    def save_notes(self, id, notes):
        """
        Set personal notes about a contact

        :param id: the ID of the contact
        :type id: str
        :returns: the unicode object to save as notes
        """
        raise NotImplementedError()

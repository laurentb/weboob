# -*- coding: utf-8 -*-

# Copyright(C) 2010-2013 Bezleputh
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

from .base import CapBaseObject, IBaseCap, StringField, DateField, IntField

__all__ = ['BaseCalendarEvent', 'ICapCalendarEvent']


def enum(**enums):
    return type('Enum', (), enums)

CATEGORIES = enum(CINE='Cinema', CONCERT='Concert', THEATRE='Theatre')
TRANSP = enum(OPAQUE='OPAQUE', TRANSPARENT='TRANSPARENT')
STATUS = enum(TENTATIVE='TENTATIVE', CONFIRMED='CONFIRMED', CANCELLED='CANCELLED')


class BaseCalendarEvent(CapBaseObject):
    """
    Represents a calendar event
    """

    url = StringField('URL of the event')
    start_date = DateField('Start date of the event')
    end_date = DateField('End date of the event')
    summary = StringField('Title of the event')
    location = StringField('Location of the event')
    category = StringField('Category of the event')
    status = StringField('Status of theevent') # (TENTATIVE, CONFIRMED, CANCELLED)
    description = StringField('Description of the event')
    transp = StringField('Describes if event is available') # (OPAQUE, TRANSPARENT)
    sequence = IntField('Nb of updates, the first is number 1')
    price = StringField('Price of the event')

    @classmethod
    def id2url(cls, _id):
        """Overloaded in child classes provided by backends."""
        raise NotImplementedError()

    @property
    def page_url(self):
        """
        Get page URL of the announce.
        """
        return self.id2url(self.id)


class ICapCalendarEvent(IBaseCap):
    """
    Capability of calendar event type sites
    """

    def list_events(self, date_from, date_to=None):
        """
        list coming event.

        :param date_from: date of beguinning of the events list
        :type date_from: date
        :param date_to: date of ending of the events list
        :type date_to: date
        :rtype: iter[:class:`BaseCalendarEvent`]
        """
        raise NotImplementedError()

    def get_event(self, _id, event=None):
        """
        Get an event from an ID.

        :param _id: id of the event
        :type _id: str
        :param event : the event
        :type event : BaseCalendarEvent
        :rtype: :class:`BaseCalendarEvent` or None is fot found.
        """
        raise NotImplementedError()

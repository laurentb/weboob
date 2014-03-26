# -*- coding: utf-8 -*-

# Copyright(C) 2013 Bezleputh
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

from weboob.capabilities.calendar import BaseCalendarEvent, TRANSP, STATUS, CATEGORIES


class BiplanCalendarEvent(BaseCalendarEvent):

    def __init__(self):
        BaseCalendarEvent.__init__(self)
        self.city = u'LILLE'
        self.location = u'19, rue Colbert'
        self.sequence = 1
        self.transp = TRANSP.TRANSPARENT
        self.status = STATUS.CONFIRMED


class BiplanCalendarEventConcert(BiplanCalendarEvent):
    def __init__(self):
        BiplanCalendarEvent.__init__(self)
        self.category = CATEGORIES.CONCERT


class BiplanCalendarEventTheatre(BiplanCalendarEvent):
    def __init__(self, _id):
        BiplanCalendarEvent.__init__(self)
        self.category = CATEGORIES.THEATRE

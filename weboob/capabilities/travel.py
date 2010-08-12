# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon, Julien Hebert
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


from datetime import time

from .base import IBaseCap, CapBaseObject


__all__ = ['Departure', 'ICapTravel', 'Station']


class ICapTravel(IBaseCap):
    def iter_station_search(self, pattern):
        """
        Iterates on search results of stations.

        @param pattern [str]  the search pattern
        @return [iter]  the of Station objects
        """
        raise NotImplementedError()

    def iter_station_departures(self, station_id, arrival_id):
        """
        Iterate on departures.

        @param station_id [id]  the station id
        @param arrival_id [id]  optionnal arrival station id
        @return [iter]  result of Departure objects
        """
        raise NotImplementedError()


class Station(CapBaseObject):
    FIELDS = ('name',)

    def __init__(self, id, name):
        CapBaseObject.__init__(self, id)
        self.name = name

    def __repr__(self):
        return "<Station id='%s' name='%s'>" % (self.id, self.name)


class Departure(CapBaseObject):
    FIELDS = ('type', 'time', 'departure_station', 'arrival_station', 'late', 'information', 'plateform')

    def __init__(self, id, _type, _time):
        CapBaseObject.__init__(self, id)

        self.type = _type
        self.time = _time
        self.departure_station = u''
        self.arrival_station = u''
        self.late = time()
        self.information = u''
        self.plateform = u''

    def __repr__(self):
        return "<Departure id='%s' type='%s' time='%s' departure='%s' arrival='%s'>" % (
            self.id, self.type, self.time.strftime('%H:%M'), self.departure_station, self.arrival_station)

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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


from datetime import date

from .base import IBaseCap, CapBaseObject


__all__ = ['ICapHousing']


class HousingPhoto(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('url', basestring)
        self.add_field('data', str)

    def __iscomplete__(self):
        return self.data

    def __str__(self):
        return self.url

    def __repr__(self):
        return u'<HousingPhoto "%s" data=%do>' % (self.id, len(self.data) if self.data else 0)

class Housing(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('title', basestring)
        self.add_field('area', int)
        self.add_field('cost', int)
        self.add_field('currency', basestring)
        self.add_field('date', date)
        self.add_field('location', basestring)
        self.add_field('station', basestring)
        self.add_field('text', basestring)
        self.add_field('phone', basestring)
        self.add_field('photos', list)

class Query(CapBaseObject):
    def __init__(self):
        CapBaseObject.__init__(self, '')
        self.add_field('cities', (list,tuple))
        self.add_field('area_min', int)
        self.add_field('area_max', int)
        self.add_field('cost_min', int)
        self.add_field('cost_max', int)

class City(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('name', basestring)

class ICapHousing(IBaseCap):
    def search_housings(self, query):
        raise NotImplementedError()

    def get_housing(self, housing):
        raise NotImplementedError()

    def search_city(self, pattern):
        raise NotImplementedError()

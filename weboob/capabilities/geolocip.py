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


from .base import IBaseCap, CapBaseObject


__all__ = ['IpLocation', 'ICapGeolocIp']


class IpLocation(CapBaseObject):
    def __init__(self, ipaddr):
        CapBaseObject.__init__(self, ipaddr)

        self.ipaddr = ipaddr
        self.add_field('city', basestring)
        self.add_field('region', basestring)
        self.add_field('zipcode', basestring)
        self.add_field('country', basestring)
        self.add_field('lt', float)
        self.add_field('lg', float)
        self.add_field('host', basestring)
        self.add_field('tld', basestring)
        self.add_field('isp', basestring)

class ICapGeolocIp(IBaseCap):
    def get_location(self, ipaddr):
        raise NotImplementedError()

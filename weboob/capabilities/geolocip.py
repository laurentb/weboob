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

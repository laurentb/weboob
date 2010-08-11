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


__all__ = ('IpLocation', 'ICapGeolocIp')

class IpLocation(object):
    def __init__(self, ipaddr):
        self.ipaddr = ipaddr
        self.city = None
        self.region = None
        self.zipcode = None
        self.country = None
        self.lt = None
        self.lg = None
        self.host = None
        self.tld = None
        self.isp = None

class ICapGeolocIp(ICap):
    def get_location(self, ipaddr):
        raise NotImplementedError()

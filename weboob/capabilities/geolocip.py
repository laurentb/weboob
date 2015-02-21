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


from .base import Capability, BaseObject, StringField, FloatField


__all__ = ['IpLocation', 'CapGeolocIp']


class IpLocation(BaseObject):
    """
    Represents the location of an IP address.
    """
    city =      StringField('City')
    region =    StringField('Region')
    zipcode =   StringField('Zip code')
    country =   StringField('Country')
    lt =        FloatField('Latitude')
    lg =        FloatField('Longitude')
    osmlink =   StringField('Link to OpenStreetMap location page')
    host =      StringField('Hostname')
    tld =       StringField('Top Level Domain')
    isp =       StringField('Internet Service Provider')

    def __init__(self, ipaddr):
        BaseObject.__init__(self, ipaddr)


class CapGeolocIp(Capability):
    """
    Access information about IP addresses database.
    """

    def get_location(self, ipaddr):
        """
        Get location of an IP address.

        :param ipaddr: IP address
        :type ipaddr: str
        :rtype: :class:`IpLocation`
        """
        raise NotImplementedError()

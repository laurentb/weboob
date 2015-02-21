# -*- coding: utf-8 -*-

# Copyright(C) 2015 Julien Veyssier
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


from weboob.capabilities.geolocip import CapGeolocIp, IpLocation
from weboob.tools.backend import Module
from weboob.browser.browsers import Browser
from weboob.tools.json import json


__all__ = ['FreegeoipModule']


class FreegeoipModule(Module, CapGeolocIp):
    NAME = 'freegeoip'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'public API to search the geolocation of IP addresses'
    BROWSER = Browser

    def get_location(self, ipaddr):
        res = self.browser.location('https://freegeoip.net/json/%s' % ipaddr.encode('utf-8'))
        jres = json.loads(res.text)

        iploc = IpLocation(ipaddr)
        iploc.city = u'%s'%jres['city']
        iploc.region = u'%s'%jres['region_name']
        iploc.zipcode = u'%s'%jres['zip_code']
        iploc.country = u'%s'%jres['country_name']
        if jres['latitude'] != '':
            iploc.lt = float(jres['latitude'])
        else:
            iploc.lt = 0.0
        if jres['longitude'] != '':
            iploc.lg = float(jres['longitude'])
        else:
            iploc.lg = 0.0

        return iploc

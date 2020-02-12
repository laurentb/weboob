# -*- coding: utf-8 -*-

# Copyright(C) 2015 Julien Veyssier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.geolocip import CapGeolocIp, IpLocation
from weboob.tools.backend import Module
from weboob.browser.browsers import Browser
from weboob.tools.json import json


__all__ = ['IpapiModule']


class IpapiModule(Module, CapGeolocIp):
    NAME = 'ipapi'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '2.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"IP-API Geolocation API"
    BROWSER = Browser

    def get_location(self, ipaddr):
        res = self.browser.location(u'http://ip-api.com/json/%s' % ipaddr)
        jres = json.loads(res.text)

        if "status" in jres and jres["status"] == "fail":
            raise Exception("IPAPI failure : %s" % jres["message"])

        iploc = IpLocation(ipaddr)
        iploc.city = u'%s'%jres['city']
        iploc.region = u'%s'%jres['regionName']
        iploc.zipcode = u'%s'%jres['zip']
        iploc.country = u'%s'%jres['country']
        if jres['lat'] != '':
            iploc.lt = float(jres['lat'])
        else:
            iploc.lt = 0.0
        if jres['lon'] != '':
            iploc.lg = float(jres['lon'])
        else:
            iploc.lg = 0.0
        #iploc.host = 'NA'
        #iploc.tld = 'NA'
        if 'isp' in jres:
            iploc.isp = u'%s'%jres['isp']

        return iploc

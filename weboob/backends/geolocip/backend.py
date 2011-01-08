# -*- coding: utf-8 -*-

# Copyright(C) 2010  Julien Veyssier
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

from __future__ import with_statement

from weboob.capabilities.geolocip import ICapGeolocIp, IpLocation
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser


__all__ = ['GeolocIpBackend']


class GeolocIpBackend(BaseBackend, ICapGeolocIp):
    NAME = 'geolocip'
    MAINTAINER = 'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.5.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"IP Adresses geolocalisation with the site www.geolocip.com"
    BROWSER = BaseBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_location(self, ipaddr):
        with self.browser:

            content = self.browser.readurl('http://www.geolocip.com/?s[ip]=%s&commit=locate+IP!' % str(ipaddr))

            tab = {}
            last_line = ''
            line = ''
            for line in content.split('\n'):
                if len(line.split('<dd>')) > 1:
                    key = last_line.split('<dt>')[1].split('</dt>')[0][0:-2]
                    value = line.split('<dd>')[1].split('</dd>')[0]
                    tab[key] = value
                last_line = line
            iploc = IpLocation(ipaddr)
            iploc.city = tab['City']
            iploc.region = tab['Region']
            iploc.zipcode = tab['Postal code']
            iploc.country = tab['Country name']
            if tab['Latitude'] != '':
                iploc.lt = float(tab['Latitude'])
            else:
                iploc.lt = 0.0
            if tab['Longitude'] != '':
                iploc.lg = float(tab['Longitude'])
            else:
                iploc.lg = 0.0
            #iploc.host = 'NA'
            #iploc.tld = 'NA'
            #iploc.isp = 'NA'

            return iploc

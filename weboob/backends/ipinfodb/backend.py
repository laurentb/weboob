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


__all__ = ['IpinfodbBackend']


class IpinfodbBackend(BaseBackend, ICapGeolocIp):
    NAME = 'ipinfodb'
    MAINTAINER = 'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.4'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"IP Adresses geolocalisation with the site ipinfodb.com"
    BROWSER = BaseBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_location(self, ipaddr):
        with self.browser:

            content = self.browser.readurl('http://ipinfodb.com/ip_locator.php?ip=%s' % str(ipaddr))

            if 'Invalid IP or domain name' in content:
                """ exception"""
                raise Exception('Bad parameter')
            else:
                tab = {}
                line = ''
                for line in content.split('\n'):
                    if '<li>' in line:
                        if 'Country :' in line:
                            tab['Country name'] = line.split('Country : ')[1].split('<')[0]
                        elif "State/Province :" in line:
                            tab['Region'] = line.split('State/Province : ')[1].split('<')[0]
                        elif "City :" in line:
                            tab['City'] = line.split('City : ')[1].split('<')[0]
                        elif "Latitude :" in line:
                            tab['Latitude'] = line.split('Latitude : ')[1].split('<')[0]
                        elif "Longitude :" in line:
                            tab['Longitude'] = line.split('Longitude : ')[1].split('<')[0]
                        elif "Hostname :" in line:
                            tab['hostname'] = line.split('Hostname : ')[1].split('<')[0]
                iploc = IpLocation(ipaddr)
                iploc.city = tab['City'].decode('utf-8')
                iploc.region = tab['Region']
                iploc.zipcode = 'NA'
                iploc.country = tab['Country name']
                iploc.lt = float(tab['Latitude'])
                iploc.lg = float(tab['Longitude'])
                iploc.host = tab['hostname']
                iploc.tld = tab['hostname'].split('.')[-1]
                #iploc.isp = 'NA'

                return iploc

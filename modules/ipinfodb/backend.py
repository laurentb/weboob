# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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

from __future__ import with_statement

from weboob.capabilities.geolocip import ICapGeolocIp, IpLocation
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser, BrowserUnavailable


__all__ = ['IpinfodbBackend']


class IpinfodbBackend(BaseBackend, ICapGeolocIp):
    NAME = 'ipinfodb'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '0.e'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"IPInfoDB IP addresses geolocation service"
    BROWSER = BaseBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_location(self, ipaddr):
        with self.browser:

            content = self.browser.readurl('http://ipinfodb.com/ip_locator.php?ip=%s' % str(ipaddr))

            if content is None:
                raise BrowserUnavailable()

            if 'Invalid IP or domain name' in content:
                raise Exception('Bad parameter')
            else:
                tab = {'City' : 'NA' ,\
                        'Country name' : 'NA' ,\
                        'Region' : 'NA' ,\
                        'Latitude' : 'NA' ,\
                        'Longitude' : 'NA' ,\
                        'hostname' : 'NA' ,\
                        'zipcode' : 'NA'}
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
                iploc.zipcode = tab['zipcode']
                iploc.country = tab['Country name']
                try :
                    iploc.lt = float(tab['Latitude'])
                    iploc.lg = float(tab['Longitude'])
                except ValueError:
                    pass
                iploc.host = tab['hostname']
                iploc.tld = tab['hostname'].split('.')[-1]
                #iploc.isp = 'NA'

                return iploc

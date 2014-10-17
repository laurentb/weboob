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


from weboob.capabilities.geolocip import CapGeolocIp, IpLocation
from weboob.tools.backend import Module
from weboob.deprecated.browser import StandardBrowser


__all__ = ['IpinfodbModule']


class IpinfodbModule(Module, CapGeolocIp):
    NAME = 'ipinfodb'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"IPInfoDB IP addresses geolocation service"
    BROWSER = StandardBrowser

    def get_location(self, ipaddr):
        self.browser.location("http://ipinfodb.com/ip_locator.php")
        self.browser.select_form(nr=0)
        self.browser['ip'] = str(ipaddr)
        response = self.browser.submit()
        document = self.browser.get_document(response)

        tab = {'City' : 'NA' ,
                'Country name' : 'NA' ,
                'Region' : 'NA' ,
                'Latitude' : 'NA' ,
                'Longitude' : 'NA' ,
                'hostname' : 'NA' ,
                'zipcode' : 'NA'}
        for li in document.getiterator('li'):
            txt = li.text_content()
            if 'Country :' in txt:
                tab['Country name'] = txt.split('Country : ')[1].split('<')[0]
            elif "State/Province :" in txt:
                tab['Region'] = txt.split('State/Province : ')[1].split('<')[0]
            elif "City :" in txt:
                tab['City'] = txt.split('City : ')[1].split('<')[0]
            elif "Latitude :" in txt:
                tab['Latitude'] = txt.split('Latitude : ')[1].split('<')[0]
            elif "Longitude :" in txt:
                tab['Longitude'] = txt.split('Longitude : ')[1].split('<')[0]
            elif "Hostname :" in txt:
                tab['hostname'] = txt.split('Hostname : ')[1].split('<')[0]
        iploc = IpLocation(ipaddr)
        iploc.city = unicode(tab['City'].decode('utf-8'))
        iploc.region = unicode(tab['Region'])
        iploc.zipcode = unicode(tab['zipcode'])
        iploc.country = unicode(tab['Country name'])
        try :
            iploc.lt = float(tab['Latitude'])
            iploc.lg = float(tab['Longitude'])
        except ValueError:
            pass
        iploc.host = unicode(tab['hostname'])
        iploc.tld = unicode(tab['hostname'].split('.')[-1])
        #iploc.isp = 'NA'

        return iploc

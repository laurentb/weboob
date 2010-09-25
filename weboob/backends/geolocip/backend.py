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

from __future__ import with_statement

from weboob.capabilities.geolocip import ICapGeolocIp, IpLocation
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BaseBrowser


__all__ = ['GeolocIpBackend']


class GeolocIpBackend(BaseBackend, ICapGeolocIp):
    NAME = 'geolocip'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.2'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"IP Adresses geolocalisation"
    CONFIG = {'email':         BaseBackend.ConfigField(description='Username on website'),
              'password':      BaseBackend.ConfigField(description='Password of account', is_masked=True),
             }
    BROWSER = BaseBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['email'], self.config['password'])

    def get_location(self, ipaddr):
        with self.browser:
            args = {'email':     self.config['email'],
                    'pass':      self.config['password'],
                    'ip':        str(ipaddr)
                   }
            content = self.browser.readurl(self.browser.buildurl('http://www.geolocalise-ip.com/api.php', **args))
            tab = {}
            for line in content.split('&'):
                if not '=' in line:
                    continue
                key, value = line.split('=', 1)
                tab[key] = value

            if 'erreur' in tab and tab['erreur'][0] == '1':
                raise Exception(tab['erreur'][1:].replace('<p>', '').replace('<br />', '\n'))

            iploc = IpLocation(ipaddr)
            iploc.city = tab['ville'].decode('iso-8859-15')
            iploc.region = tab['region']
            iploc.zipcode = tab['cp']
            iploc.country = tab['pays']
            iploc.lt = float(tab['lt'])
            iploc.lg = float(tab['lg'])
            iploc.host = tab['host']
            iploc.tld = tab['tld']
            iploc.isp = tab['fai']
            return iploc

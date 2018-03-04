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


from weboob.capabilities.geolocip import CapGeolocIp
from weboob.tools.backend import Module

from .browser import IpinfodbBrowser


__all__ = ['IpinfodbModule']


class IpinfodbModule(Module, CapGeolocIp):
    NAME = 'ipinfodb'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"IPInfoDB IP addresses geolocation service"
    BROWSER = IpinfodbBrowser

    def get_location(self, ipaddr):
        return self.browser.get_location(ipaddr)

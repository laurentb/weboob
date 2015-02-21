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

from __future__ import print_function

from weboob.capabilities.geolocip import CapGeolocIp
from weboob.tools.application.repl import ReplApplication


__all__ = ['Geolooc']


class Geolooc(ReplApplication):
    APPNAME = 'geolooc'
    VERSION = '1.1'
    COPYRIGHT = 'Copyright(C) 2010-YEAR Romain Bignon'
    DESCRIPTION = "Console application allowing to geolocalize IP addresses."
    SHORT_DESCRIPTION = "geolocalize IP addresses"
    CAPS = CapGeolocIp

    def main(self, argv):
        if len(argv) < 2:
            print('Syntax: %s ipaddr' % argv[0], file=self.stderr)
            return 2

        for location in self.do('get_location', argv[1]):
            if location.lt and location.lg:
                location.osmlink = u'http://www.openstreetmap.org/?mlat=%s&mlon=%s#map=13/%s/%s' % (location.lt, location.lg, location.lt, location.lg)
            self.format(location)

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


import sys

from weboob.capabilities.geolocip import ICapGeolocIp
from weboob.tools.application.repl import ReplApplication


__all__ = ['Geolooc']


class Geolooc(ReplApplication):
    APPNAME = 'geolooc'
    VERSION = '0.6'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'
    DESCRIPTION = "Geolooc is a console application to get geolocalization of IP addresses."
    CAPS = ICapGeolocIp

    def main(self, argv):
        if len(argv) < 2:
            print >>sys.stderr, 'Syntax: %s ipaddr' % argv[0]
            return 1

        for backend, location in self.do('get_location', argv[1]):
            self.format(location)

        return 0

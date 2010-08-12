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


import logging

from weboob.capabilities.geolocip import ICapGeolocIp
from weboob.tools.application.console import ConsoleApplication


__all__ = ['Geolooc']


class Geolooc(ConsoleApplication):
    APPNAME = 'geolooc'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon'

    def main(self, argv):
        if len(argv) < 2:
            print >>sys.stderr, 'Syntax: %s ipaddr' % argv[0]
            return 1

        self.load_configured_backends(ICapGeolocIp)
        for backend, location in self.do('get_location', argv[1]):
            self.format(location, backend.name)

        return 0

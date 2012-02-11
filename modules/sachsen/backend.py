# -*- coding: utf-8 -*-

# Copyright(C) 2010,2011  Romain Bignon, Florent Fourcot
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

from .browser import SachsenBrowser
from weboob.capabilities.gauge import ICapWaterLevel
from weboob.tools.backend import BaseBackend


__all__ = ['SachsenLevelBackend']


class SachsenLevelBackend(BaseBackend, ICapWaterLevel):
    NAME = 'sachsen'
    MAINTAINER = 'Florent Fourcot'
    EMAIL = ''
    VERSION = '0.b'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"Level of Sachsen river"
    BROWSER = SachsenBrowser

    def create_default_browser(self):
        return self.create_browser()

    def get_list(self):
        return self.browser.get_rivers_list()

    def get_history(self, id):
        return self.browser.get_history(id)

    def last(self, id):
        return self.browser.last_seen(id)
 
    def search(self, pattern):
        return self.browser.search(pattern)

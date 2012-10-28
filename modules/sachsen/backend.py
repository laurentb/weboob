# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon, Florent Fourcot
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

from .browser import SachsenBrowser
from weboob.capabilities.gauge import ICapWaterLevel
from weboob.tools.backend import BaseBackend


__all__ = ['SachsenLevelBackend']


class SachsenLevelBackend(BaseBackend, ICapWaterLevel):
    NAME = 'sachsen'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.e'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u"Level of Sachsen river"
    BROWSER = SachsenBrowser

    def iter_gauge_history(self, id):
        return self.browser.iter_history(id)

    def get_last_measure(self, id):
        return self.browser.last_seen(id)

    def iter_gauges(self, pattern=None):
        if pattern is None:
            return self.browser.get_rivers_list()
        else:
            return self.browser.search(pattern)

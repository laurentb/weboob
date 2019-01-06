# -*- coding: utf-8 -*-

# Copyright(C) 2014 Florent Fourcot
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

from weboob.tools.backend import Module
from weboob.capabilities.parcel import CapParcel

from .browser import ColispriveBrowser

__all__ = ['ColispriveModule']


class ColispriveModule(Module, CapParcel):
    NAME = 'colisprive'
    DESCRIPTION = u'Colisprive parcel tracking website'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'

    BROWSER = ColispriveBrowser

    def get_parcel_tracking(self, _id):
        return self.browser.get_tracking_info(_id)

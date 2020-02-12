# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.capabilities.parcel import CapParcel
from weboob.tools.backend import Module

from .browser import ChronopostBrowser


__all__ = ['ChronopostModule']


class ChronopostModule(Module, CapParcel):
    NAME = 'chronopost'
    DESCRIPTION = u'Chronopost'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '2.1'

    BROWSER = ChronopostBrowser

    def get_parcel_tracking(self, id):
        return self.browser.get_tracking_info(id)

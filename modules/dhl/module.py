# -*- coding: utf-8 -*-

# Copyright(C) 2015      Matthieu Weber
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


from weboob.tools.backend import Module
from weboob.capabilities.parcel import CapParcel, ParcelNotFound

from .browser import DHLExpressBrowser, DeutschePostDHLBrowser


__all__ = ['DHLModule']


class DHLModule(Module, CapParcel):
    NAME = 'dhl'
    DESCRIPTION = u'DHL website'
    MAINTAINER = u'Matthieu Weber'
    EMAIL = 'mweber+weboob@free.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'

    def get_parcel_tracking(self, id):
        """
        Get information abouut a parcel.

        :param id: ID of the parcel
        :type id: :class:`str`
        :rtype: :class:`Parcel`
        :raises: :class:`ParcelNotFound`
        """
        self._browser = None
        if len(id) == 10 or len(id) == 20:
            self.BROWSER = DHLExpressBrowser
        elif len(id) == 12 or len(id) == 16:
            self.BROWSER = DeutschePostDHLBrowser
        else:
            ParcelNotFound("Wrong length for ID: %s" % id)

        return self.browser.get_tracking_info(id)

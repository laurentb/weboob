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
from weboob.capabilities.parcel import CapParcel

from .browser import DPDBrowser


__all__ = ['DPDModule']


class DPDModule(Module, CapParcel):
    NAME = 'dpd'
    DESCRIPTION = u'DPD website'
    MAINTAINER = u'Matthieu Weber'
    EMAIL = 'mweber+weboob@free.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = DPDBrowser

    def get_parcel_tracking(self, id):
        """
        Get information abouut a parcel.

        :param id: ID of the parcel
        :type id: :class:`str`
        :rtype: :class:`Parcel`
        :raises: :class:`ParcelNotFound`
        """
        return self.browser.get_tracking_info(id)

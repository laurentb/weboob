# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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

from weboob.capabilities.parcel import CapParcel, ParcelNotFound, Parcel
from weboob.tools.backend import Module

from .browser import ColissimoBrowser

__all__ = ['ColissimoModule']


class ColissimoModule(Module, CapParcel):
    NAME = 'colissimo'
    DESCRIPTION = u'Colissimo parcel tracking website'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '2.0'
    LICENSE = 'AGPLv3+'

    BROWSER = ColissimoBrowser

    def get_parcel_tracking(self, _id):
        # 13 is the magic length of colissimo tracking ids
        if len(_id) != 13:
            raise ParcelNotFound(u"Colissimo ID's must have 13 print character")

        events = self.browser.get_tracking_info(_id)
        p = Parcel(_id)
        p.history = events

        first = events[0]
        p.info = first.activity

        if u"remis au gardien ou" in p.info or u"Votre colis est livré" in p.info:
            p.status = p.STATUS_ARRIVED
        elif u"pas encore pris en charge par La Poste" in p.info:
            p.status = p.STATUS_PLANNED
        else:
            p.status = p.STATUS_IN_TRANSIT

        return p

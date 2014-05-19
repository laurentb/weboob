# -*- coding: utf-8 -*-

# Copyright(C) 2013 Florent Fourcot
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

from weboob.capabilities.parcel import ICapParcel, Parcel, Event
from weboob.capabilities.base import UserError
from weboob.tools.backend import BaseBackend

from .browser import ColissimoBrowser
from datetime import date

__all__ = ['ColissimoBackend']


class ColissimoBackend(BaseBackend, ICapParcel):
    NAME = 'colissimo'
    DESCRIPTION = u'Colissimo parcel tracking website'
    MAINTAINER = u'Florent Fourcot'
    EMAIL = 'weboob@flo.fourcot.fr'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'

    BROWSER = ColissimoBrowser

    def get_parcel_tracking(self, _id):
        # 13 is the magic length of colissimo tracking ids
        if len(_id) != 13:
            raise UserError(u"Colissimo ID's must have 13 print character")
        data = self.browser.get_tracking_info(_id)
        p = Parcel(_id)
        label = data['message']
        if data['error']:
            raise UserError(u"label")
        p.info = label
        # TODO, need to know the delivery message
        if u"remis au gardien ou" in label or u"Votre colis est livré" in label:
            p.status = p.STATUS_ARRIVED
        elif u"pas encore pris en charge par La Poste" in label:
            p.status = p.STATUS_PLANNED
        else:
            p.status = p.STATUS_IN_TRANSIT

        ev = Event(0)
        ev.activity = label
        ev.date = date(*reversed([int(x) for x in data['date'].split("/")]))
        p.history = [ev]

        return p

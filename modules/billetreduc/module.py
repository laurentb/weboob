# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals


from weboob.tools.backend import Module
from weboob.capabilities.calendar import CapCalendarEvent, CATEGORIES

from .browser import BilletreducBrowser


__all__ = ['BilletreducModule']


class BilletreducModule(Module, CapCalendarEvent):
    NAME = 'billetreduc'
    DESCRIPTION = u'BilletReduc discount ticket reservation'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = BilletreducBrowser

    ASSOCIATED_CATEGORIES = (
        CATEGORIES.CINE,
        CATEGORIES.CONCERT,
        CATEGORIES.CONF,
        CATEGORIES.EXPO,
        CATEGORIES.SPECTACLE,
        CATEGORIES.SPORT,
        CATEGORIES.THEATRE,
    )

    def get_event(self, _id):
        return self.browser.get_event(_id)

    def list_events(self, date_from, date_to=None):
        raise NotImplementedError()

    def search_events(self, query):
        return self.browser.search_events(query)

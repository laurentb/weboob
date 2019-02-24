# -*- coding: utf-8 -*-

# Copyright(C) 2018      Vincent A
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

from __future__ import unicode_literals


from weboob.tools.backend import Module
from weboob.capabilities.contact import CapDirectory, Place

from .browser import PagesjaunesBrowser


__all__ = ['PagesjaunesModule']


class PagesjaunesModule(Module, CapDirectory):
    NAME = 'pagesjaunes'
    DESCRIPTION = 'Pages Jaunes'
    MAINTAINER = 'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'

    BROWSER = PagesjaunesBrowser

    def search_contacts(self, query, sortby):
        return self.browser.search_contacts(query)

    def fill_contact(self, obj, fields):
        if 'opening' in fields:
            self.browser.fill_hours(obj)

    OBJECTS = {
        Place: fill_contact,
    }


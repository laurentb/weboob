# -*- coding: utf-8 -*-

# Copyright(C) 2016      Phyks
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


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.calendar import CapCalendarEvent

from .browser import CentQuatreBrowser

__all__ = ['CentQuatreModule']


class CentQuatreModule(Module, CapCalendarEvent):
    NAME = 'centquatre'
    DESCRIPTION = u'centquatre website'
    MAINTAINER = u'Phyks'
    EMAIL = 'phyks@phyks.me'
    LICENSE = 'AGPLv3+'
    VERSION = '2.0'
    BROWSER = CentQuatreBrowser

    CONFIG = BackendConfig(
        Value('email', label='Username', default=''),
        ValueBackendPassword('password', label='Password', default='')
    )

    def create_default_browser(self):
        email = self.config['email'].get()
        password = self.config['password'].get()
        return self.create_browser(email, password)

    def get_event(self, _id):
        return self.browser.get_event(_id)

    def list_events(self, date_from, date_to=None):
        return self.browser.list_events(date_from, date_to)

    def search_events(self, query):
        if self.has_matching_categories(query):
            return self.browser.search_events(query)

# -*- coding: utf-8 -*-

# Copyright(C) 2017 Laurent Bachelier
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
from weboob.tools.capabilities.paste import BasePasteModule

from .browser import SprungeBrowser, SprungePaste


class SprungeModule(Module, BasePasteModule):
    NAME = 'sprunge'
    MAINTAINER = u'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '2.1'
    DESCRIPTION = u'Sprunge text sharing tool'
    LICENSE = 'AGPLv3+'
    BROWSER = SprungeBrowser

    EXPIRATIONS = {
        False: 'f',
    }

    def new_paste(self, *args, **kwargs):
        return SprungePaste(*args, **kwargs)

    def can_post(self, contents, title=None, public=None, max_age=None):
        if public is True:
            return 0
        if max_age is not None:
            if self.get_closest_expiration(max_age) is None:
                return 0
        if not title:
            return 2
        return 1

    def get_paste(self, _id):
        return self.browser.get_paste(_id)

    def fill_paste(self, paste, fields):
        self.browser.fill_paste(paste)
        return paste

    def post_paste(self, paste, max_age=None):
        self.browser.post_paste(paste)

    OBJECTS = {SprungePaste: fill_paste}

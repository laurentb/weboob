# -*- coding: utf-8 -*-

# Copyright(C) 2011 Laurent Bachelier
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


from weboob.capabilities.paste import ICapPaste
from weboob.tools.backend import BaseBackend
from weboob.capabilities.base import NotLoaded

from .browser import PastealaconBrowser
from .paste import PastealaconPaste


__all__ = ['PastealaconBackend']


class PastealaconBackend(BaseBackend, ICapPaste):
    NAME = 'pastealacon'
    MAINTAINER = 'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '0.8'
    DESCRIPTION = 'Paste a la con paste tool'
    LICENSE = 'AGPLv3+'
    BROWSER = PastealaconBrowser

    def get_paste(self, _id):
        return PastealaconPaste(_id)

    def fill_paste(self, paste, fields):
        # if we only want the contents
        if fields == ['contents']:
            if paste.contents is NotLoaded:
                contents = self.browser.get_contents(paste.id)
                paste.contents = contents
        elif fields:
            self.browser.fill_paste(paste)
        return paste

    def post_paste(self, paste):
        self.browser.post_paste(paste)

    OBJECTS = {PastealaconPaste: fill_paste}

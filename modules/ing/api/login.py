# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from io import BytesIO

from weboob.browser.pages import JsonPage
from weboob.browser.filters.json import Dict

from .transfer_page import TransferINGVirtKeyboard


class LoginPage(JsonPage):
    @property
    def is_logged(self):
        return 'firstName' in self.doc

    def init_vk(self, img, password):
        pin_position = Dict('pinPositions')(self.doc)
        image = BytesIO(img)

        vk = TransferINGVirtKeyboard(image, cols=5, rows=2, browser=self.browser)
        password_random_coords = vk.password_tiles_coord(password)
        # pin positions (website side) start at 1, our positions start at 0
        return [password_random_coords[index - 1] for index in pin_position]

    def get_password_coord(self, img, password):
        assert 'pinPositions' in self.doc, 'Virtualkeyboard position has failed'
        assert 'keyPadUrl' in self.doc, 'Virtualkeyboard image url is missing'
        return self.init_vk(img, password)

    def get_keypad_url(self):
        return Dict('keyPadUrl')(self.doc)

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

from io import BytesIO
from PIL import Image, ImageFilter
import random

from weboob.tools.captcha.virtkeyboard import SimpleVirtualKeyboard
from weboob.browser.pages import JsonPage
from weboob.browser.filters.json import Dict


class INGVirtKeyboard(SimpleVirtualKeyboard):
    # from parent
    tile_margin = 10
    convert = 'RGB'

    # for children
    safe_tile_margin = 10
    small_img_size = (15, 14)
    alter_img_params = {
        'radius': 2,
        'percent': 95,
        'threshold': 3,
        'limit_pixel': 200
    }

    # for matching_symbols_coords, indexes are cases place like this
    #  ---  ---  ---  ---  ---
    #  |0|  |1|  |2|  |3|  |4|
    #  ---  ---  ---  ---  ---
    #  ---  ---  ---  ---  ---
    #  |5|  |6|  |7|  |8|  |9|
    #  ---  ---  ---  ---  ---
    matching_symbols_coords = {
        '0': (3, 3, 93, 91),
        '1': (99, 3, 189, 91),
        '2': (196, 3, 286, 91),
        '3': (293, 3, 383, 91),
        '4': (390, 3, 480, 91),
        '5': (3, 98, 93, 186),
        '6': (99, 98, 189, 186),
        '7': (196, 98, 286, 186),
        '8': (293, 98, 383, 186),
        '9': (390, 98, 480, 186),
    }

    symbols = {
        '0': ('7b4989b431e631ec79df5d71aecb1a47','e2522e1f7476ad6430219a73b10799b0', 'f7db285c5c742c3a348e332c0e9f7f3e',),
        '1': ('9f1b03aa9a6f9789714c38eb90a43a11', '86bc0e7e1173472928e746db874b38c3',),
        '2': ('3a7d1ba32f4326a02f717f71262ba02b', 'afc2a00289ba9e362c4e9333c14a574a',),
        '3': ('203bfd122f474eb9c5c278eeda01bed4', 'c1daa556a1eff1fd18817dbef39792f8',),
        '4': ('c09b323e5a80a195d9cb0c3000f3d7ec', 'f020eaf7cdffefec065d3b2801ed73e2', '5e194b0aae3b8f02ebbf9cdec5c37239',),
        '5': ('1749dc3f2e302cd3562a0558755ab030', 'b64163e3f5f7d83ff1baad8c4d1bc37b',),
        '6': ('0888a7dc9085fcf09d56363ac253a54a', 'e269686d10f95678caf995de6834f74b', '8c505dad47cf6029921fca5fb4b0bc8d',),
        '7': ('75aaa903b8277b82c458c3540208a009', 'e97b0c0e01d77dd480b8a5f5c138a268',),
        '8': ('f5fa36d16f55b72ba988eb87fa1ed753', '118a52a6a480b5db5eabb0ea26196db3',),
        '9': ('62f91d10650583cb6146d25bb9ac161d', 'fd81675aa1c26cbf5bb6c9f1bcdbbdf9',),
    }

    def __init__(self, file, cols, rows, browser):
        # use matching_symbols_coords because margins between tiles are not equals
        super(INGVirtKeyboard, self).__init__(file=file, cols=cols, rows=rows, matching_symbols_coords=self.matching_symbols_coords, browser=browser)

    def process_tiles(self):
        for tile in self.tiles:
            # format tile object like:
            # `tile.original_img`: original tile image size
            # `tile.coords`: original tile image coords
            # `tile.image`: resized and altered image tile
            # `tile.md5`: image tile resized hash
            tile.original_img = tile.image
            tile.image = tile.image.resize(self.small_img_size, resample=Image.BILINEAR)

            # convert to monochrome image
            tile.image = tile.image.convert('L')
            # See ImageFilter.UnsharpMask from Pillow
            tile.image = tile.image.filter(ImageFilter.UnsharpMask(
                radius=self.alter_img_params['radius'],
                percent=self.alter_img_params['percent'],
                threshold=self.alter_img_params['threshold'])
            )
            tile.image = Image.eval(tile.image, lambda px: 0 if px <= self.alter_img_params['limit_pixel'] else 255)

    def cut_tiles(self, tile_margin=None):
        assert self.tiles, 'There are no tiles to process'
        super(INGVirtKeyboard, self).cut_tiles(tile_margin)

        # alter tile
        self.process_tiles()

    def password_tiles_coord(self, password):
        password_tiles = []

        for digit in password:
            for tile in self.tiles:
                if tile.md5 in self.symbols[digit]:
                    password_tiles.append(tile)
                    break
            else:
                # Dump file only when the symbol is not found
                self.dump_tiles(self.path)
                raise Exception("Symbol '%s' not found; all symbol hashes are available in %s"
                                % (digit, self.path))

        formatted_password = []
        for tile in password_tiles:
            formatted_password.append([
                random.uniform(tile.coords[0], tile.coords[2]),
                random.uniform(tile.coords[1], tile.coords[3]),
            ])
        return formatted_password


class LoginPage(JsonPage):
    @property
    def is_logged(self):
        return 'firstName' in self.doc

    def get_password_coord(self, img, password):
        assert 'pinPositions' in self.doc, 'Virtualkeyboard position has failed'
        assert 'keyPadUrl' in self.doc, 'Virtualkeyboard image url is missing'

        pin_position = Dict('pinPositions')(self.doc)
        image = BytesIO(img)

        vk = INGVirtKeyboard(image, cols=5, rows=2, browser=self.browser)
        password_random_coords = vk.password_tiles_coord(password)
        # pin positions (website side) start at 1, our positions start at 0
        return [password_random_coords[index-1] for index in pin_position]

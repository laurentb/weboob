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
    tile_margin = 3
    margin = (0, 4, 0, 0)
    convert = 'RGB'

    symbols = {
        '0': ('117b18365105224c7207d3ec0ce7516f',),
        '1': ('112a72c31ebdf0cdafb84e67c6e1f8f2',),
        '2': ('df8534cb28a19e600976d39af2c4f6fe',),
        '3': ('911dbe595604da336fbdd360f89bada1',),
        '4': ('8a22058801980e4afb25c414e388bfa8',),
        '5': ('c7d430083b55fbe2834c912c7cded124', 'a85d836c231f9e2ee30adbfb8e3f8d96'),
        '6': ('64f8b9f3a93bc534443646f0b54e26ad',),
        '7': ('6c14303e9bffdcd1880ce415b6f0efb2',),
        '8': ('a62e9e25b047160090de1634c8d3b0f6',),
        '9': ('2b9bc97ce4ccc67d4ae0c3ca54957b33', 'afc9d2840290b7da08bf1d0b27b6c302'),
    }

    # Clean image
    def alter_image(self):
        # original image size is (484, 190), save the original image
        self.original_image = self.image

        # create miniature of image to get more reliable hash
        self.image = self.image.resize((100, 40), resample=Image.BILINEAR)
        # See ImageFilter.UnsharpMask from Pillow
        self.image = self.image.filter(ImageFilter.UnsharpMask(radius=2, percent=135, threshold=3))
        self.image = Image.eval(self.image, lambda px: 0 if px <= 160 else 255)

    def password_tiles_coord(self, password):
        # get image original size to get password coord
        image_width, image_height = self.original_image.size
        tile_width, tile_height = image_width // self.cols, image_height // self.rows

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
        safe_margin = 10
        for tile in password_tiles:
            # default matching_symbol is str(range(cols*rows))
            x0 = (int(tile.matching_symbol) % self.cols) * tile_width
            y0 = (int(tile.matching_symbol) // self.cols) * tile_height
            tile_original_coords = (
                x0 + safe_margin, y0 + safe_margin,
                x0 + tile_width - safe_margin, y0 + tile_height - safe_margin,
            )
            formatted_password.append([
                random.uniform(tile_original_coords[0], tile_original_coords[2]),
                random.uniform(tile_original_coords[1], tile_original_coords[3]),
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

        vk = INGVirtKeyboard(image, 5, 2, browser=self.browser)
        password_radom_coords = vk.password_tiles_coord(password)
        # pin positions (website side) start at 1, our positions start at 0
        return [password_radom_coords[index-1] for index in pin_position]

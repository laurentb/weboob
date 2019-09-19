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

import random
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageFilter

from weboob.tools.captcha.virtkeyboard import SimpleVirtualKeyboard

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Env, Field, Date
from weboob.capabilities.bank import (
    Recipient, RecipientInvalidIban, RecipientInvalidOTP,
)


class TransferINGVirtKeyboard(SimpleVirtualKeyboard):
    tile_margin = 5
    convert = 'RGB'

    safe_tile_margin = 50
    small_img_size = (125, 50) # original image size is (2420, 950)
    alter_img_params = {
        'radius': 2,
        'percent': 150,
        'threshold': 3,
        'limit_pixel': 125
    }

    symbols = {
        '0': 'e3e62175aa1a5ef8dc67639194caa880',
        '1': '80245727e4e5f123fd64bbb1fa80dde0',
        '2': '62cfc40429652190c996db741ac90830',
        '3': 'bb2f87d32f688679745fe95ac31b80fd',
        '4': 'a4b5e16c64817deb12ca6311cb98e59a',
        '5': '56a8f3b4f068f9e2f93c4daa3a53dc17',
        '6': 'b50f7e4a375153b9f6b029dc9b0a7e64',
        '7': 'd52320c62c6157d0cadbb7a186153628',
        '8': 'dd3fb25fc7f0765610b0ffe47da85330',
        '9': 'ca55399a5b36da3fedcd1dbb73d72a2f'
    }

    # Clean image
    def alter_image(self):
        # original image size is (484, 190), save the original image
        self.original_image = self.image

        # create miniature of image to get more reliable hash
        self.image = self.image.resize(self.small_img_size, resample=Image.BILINEAR)
        # See ImageFilter.UnsharpMask from Pillow
        self.image = self.image.filter(ImageFilter.UnsharpMask(
            radius=self.alter_img_params['radius'],
            percent=self.alter_img_params['percent'],
            threshold=self.alter_img_params['threshold'])
        )
        self.image = Image.eval(self.image, lambda px: 0 if px <= self.alter_img_params['limit_pixel'] else 255)

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
        safe_margin = self.safe_tile_margin
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

class DebitAccountsPage(LoggedPage, JsonPage):
    def get_debit_accounts_uid(self):
        return [Dict('uid')(recipient) for recipient in self.doc]


class CreditAccountsPage(LoggedPage, JsonPage):
    @method
    class iter_recipients(DictElement):
        class item(ItemElement):
            def condition(self):
                return Dict('uid')(self) != Env('acc_uid')(self)

            klass = Recipient

            def obj__is_internal_recipient(self):
                return bool(Dict('ledgerBalance', default=None)(self))

            obj_id = Dict('uid')
            obj_enabled_at = datetime.now().replace(microsecond=0)

            def obj_label(self):
                if Field('_is_internal_recipient')(self):
                    return Dict('type/label')(self)
                return Dict('owner')(self)

            def obj_category(self):
                if Field('_is_internal_recipient')(self):
                    return 'Interne'
                return 'Externe'


class TransferPage(LoggedPage, JsonPage):
    @property
    def suggested_date(self):
        return Date(Dict('executionSuggestedDate'), dayfirst=True)(self.doc)

    def get_password_coord(self, password):
        assert Dict('pinValidateResponse', default=None)(self.doc), "Transfer virtualkeyboard position has failed"

        pin_position = Dict('pinValidateResponse/pinPositions')(self.doc)

        image_url = '/secure/api-v1%s' % Dict('pinValidateResponse/keyPadUrl')(self.doc)
        image = BytesIO(self.browser.open(image_url, headers={'Referer': self.browser.absurl('/secure/transfers/new')}).content)

        vk = TransferINGVirtKeyboard(image, cols=5, rows=2, browser=self.browser)
        password_random_coords = vk.password_tiles_coord(password)
        # pin positions (website side) start at 1, our positions start at 0
        return [password_random_coords[index-1] for index in pin_position]

    @property
    def transfer_is_validated(self):
        return Dict('acknowledged')(self.doc)


class AddRecipientPage(LoggedPage, JsonPage):
    def check_recipient(self, recipient):
        rcpt = self.doc
        return rcpt['accountHolderName'] == recipient.label and rcpt['iban'] == recipient.iban

    def handle_error(self):
        if 'error' in self.doc:
            if self.doc['error']['code'] == 'EXTERNAL_ACCOUNT.IBAN_NOT_FRENCH':
                # not using the bank message because it is too generic
                raise RecipientInvalidIban(message="L'IBAN doit correpondre à celui d'une banque domiciliée en France.")
            assert False, 'Recipient error not handled'


class OtpChannelsPage(LoggedPage, JsonPage):
    def get_sms_info(self):
        # receive a list of dict
        for element in self.doc:
            if element['type'] == 'SMS_MOBILE':
                return element
        assert False, 'No sms info found'


class ConfirmOtpPage(LoggedPage, JsonPage):
    def handle_error(self):
        if 'error' in self.doc:
            error_code = self.doc['error']['code']
            if error_code == 'SCA.WRONG_OTP_ATTEMPT':
                raise RecipientInvalidOTP(message=self.doc['error']['message'])

            assert False, 'Recipient OTP error not handled'

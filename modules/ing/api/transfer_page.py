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

from datetime import datetime
from io import BytesIO

from weboob.browser.pages import LoggedPage, JsonPage
from weboob.browser.elements import method, DictElement, ItemElement
from weboob.browser.filters.json import Dict
from weboob.browser.filters.standard import Env, Field, Date
from weboob.capabilities.bank import Recipient

from .login import INGVirtKeyboard


class TransferINGVirtKeyboard(INGVirtKeyboard):
    # from grand parent
    tile_margin = 5
    margin = None
    convert = 'RGB'

    # from parent
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
        return Date(Dict('pinValidateResponse/executionSuggestedDate'), dayfirst=True)(self.doc)

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

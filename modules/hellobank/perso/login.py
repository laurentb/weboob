# -*- coding: utf-8 -*-

# Copyright(C) 2013 Christophe Lampin
# Copyright(C) 2009-2011  Romain Bignon, Pierre Mazière
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


import time
import re

from weboob.deprecated.browser import Page, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import VirtKeyboard, VirtKeyboardError


class HelloBankVirtKeyboard(VirtKeyboard):
    symbols = {'0': '4d1e060efb694ee60e4bd062d800401c',
               '1': '509134b5c09980e282cdd5867815e9e3',
               '2': '4cd09c9c44405e00b12e0371e2f972ae',
               '3': '227d854efc5623292eda4ca2f9bfc4d7',
               '4': 'be8d23e7f5fce646193b7b520ff80443',
               '5': '5fe450b35c946c3a983f1df6e5b41fd1',
               '6': '113a6f63714f5094c7f0b25caaa66f78',
               '7': 'de0e93ba880a8a052aea79237f08f3f8',
               '8': '3d70474c05c240b606556c89baca0568',
               '9': '040954a5e5e93ec2fb03ac0cfe592ac2'
               }

    url = "/NSImgBDGrille?timestamp=%d"

    color = 17

    def __init__(self, basepage):
        coords = {}
        coords["01"] = (31, 28, 49, 49)
        coords["02"] = (108, 28, 126, 49)
        coords["03"] = (185, 28, 203, 49)
        coords["04"] = (262, 28, 280, 49)
        coords["05"] = (339, 28, 357, 49)
        coords["06"] = (31, 100, 49, 121)
        coords["07"] = (108, 100, 126, 121)
        coords["08"] = (185, 100, 203, 121)
        coords["09"] = (262, 100, 280, 121)
        coords["10"] = (339, 100, 357, 121)

        VirtKeyboard.__init__(self, basepage.browser.openurl(self.url % time.time()), coords, self.color)
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code = VirtKeyboard.get_symbol_code(self, md5sum)
        return code

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(Page):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        try:
            vk = HelloBankVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s" % err)
            return False

        self.browser.select_form('logincanalnet')
        self.browser.set_all_readonly(False)
        self.browser['ch1'] = login.encode('utf-8')
        self.browser['ch5'] = vk.get_string_code(password)
        self.browser.submit()


class ConfirmPage(Page):
    def get_error(self):
        for td in self.document.xpath('//td[@class="hdvon1"]'):
            if td.text:
                return td.text.strip()
        return None

    def get_relocate_url(self):
        script = self.document.xpath('//script')[0]
        m = re.match('document.location.replace\("(.*)"\)', script.text[script.text.find('document.location.replace'):])
        if m:
            return m.group(1)


class InfoMessagePage(Page):
    def on_loaded(self):
        pass

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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


import hashlib

import re
import lxml.etree as etree

from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import VirtKeyboard

__all__ = ['LoginPage', 'BadLoginPage', 'AccountDesactivate', 'Initident', 'CheckPassword', 'repositionnerCheminCourant', 'UnavailablePage']


def md5(f):
    md5 = hashlib.md5()
    md5.update(f.read())
    return md5.hexdigest()


class UnavailablePage(BasePage):
    def on_loaded(self):
        raise BrowserUnavailable()

class Keyboard(VirtKeyboard):
    symbols={'0':'daa52d75287bea58f505823ef6c8b96c',
             '1':'f5da96c2592803a8cdc5a928a2e4a3b0',
             '2':'9ff78367d5cb89cacae475368a11e3af',
             '3':'908a0a42a424b95d4d885ce91bc3d920',
             '4':'3fc069f33b801b3d0cdce6655a65c0ac',
             '5':'58a2afebf1551d45ccad79fad1600fc3',
             '6':'7fedfd9e57007f2985c3a1f44fb38ea1',
             '7':'389b8ef432ae996ac0141a2fcc7b540f',
             '8':'bf357ff09cc29ea544991642cd97d453',
             '9':'b744015eb89c1b950e13a81364112cd6'
            }

    color=(0xff, 0xff, 0xff)

    def __init__(self, page):
        img_url = re.search('background:url\((.*?)\)',etree.tostring(page.document)).group(1)
        coords = {}

        size = 252
        x, y, width, height = (0, 0, size/4, size/4)
        for i,a in enumerate(page.document.xpath('//div[@id="imageclavier"]//button')):
            code = '%02d' % i
            coords[code] = (x+8, y+8, x+height-8, y+height-8)
            if (x + width + 1) >= size:
                y += height
                x = 0
            else:
                x += width

        VirtKeyboard.__init__(self, page.browser.openurl(img_url), coords, self.color)

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code = VirtKeyboard.get_symbol_code(self,md5sum)
        return '%02d' % int(code.split('_')[-1])

    def get_string_code(self,string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def get_symbol_coords(self, (x1, y1, x2, y2)):
        # strip borders
        return VirtKeyboard.get_symbol_coords(self, (x1+3, y1+3, x2-3, y2-3))

class LoginPage(BasePage):
    def login(self, login, pwd):
        vk = Keyboard(self)

        self.browser.select_form(name='formAccesCompte')
        self.browser.set_all_readonly(False)
        self.browser['password'] = vk.get_string_code(pwd)
        self.browser['username'] = login.encode(self.browser.ENCODING)
        self.browser.submit()


class repositionnerCheminCourant(BasePage):
    def on_loaded(self):
        self.browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/securite/authentification/initialiser-identif.ea")


class Initident(BasePage):
    def on_loaded(self):
        self.browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/securite/authentification/verifierMotDePasse-identif.ea")


class CheckPassword(BasePage):
    def on_loaded(self):
        self.browser.open("https://voscomptesenligne.labanquepostale.fr/voscomptes/canalXHTML/comptesCommun/synthese_assurancesEtComptes/init-synthese.ea")


class BadLoginPage(BasePage):
    pass


class AccountDesactivate(BasePage):
    pass

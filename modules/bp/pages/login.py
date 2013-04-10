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

from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard

__all__ = ['LoginPage', 'BadLoginPage', 'AccountDesactivate', 'Initident', 'CheckPassword', 'repositionnerCheminCourant', 'UnavailablePage']


def md5(f):
    md5 = hashlib.md5()
    md5.update(f.read())
    return md5.hexdigest()


class UnavailablePage(BasePage):
    def on_loaded(self):
        raise BrowserUnavailable()

class VirtKeyboard(MappedVirtKeyboard):
    symbols={'0':'18b66bc587a29742cbce4e10b7f1cb3f',
             '1':'8f21fb2dddd2e4751b3c2347e5b991cb',
             '2':'ae90fc2f7e44ab03e8eb0a6f2a8fcdfd',
             '3':'35f1cc1a07dc1c1410761f56d37ac5f2',
             '4':'86f286828f95846f5cde187436e53855',
             '5':'6e08bc067ab243cb564226aba5e1ca1e',
             '6':'ada513599ea3c98ad882ed9ffcd4b139',
             '7':'ed13fea6185f3cbca43023374b5f41be',
             '8':'ab4317d59ce2a7b1fd2e298af5785b10',
             '9':'8c165ad38c1eb72200e6011636c4c9b6'
            }

    color=(0xff, 0xff, 0xff)

    def __init__(self, page):
        img = page.document.find("//img[@usemap='#map']")
        img_file = page.browser.openurl(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, img_file, page.document, img, self.color, map_attr='id')

        self.check_symbols(self.symbols, page.browser.responses_dirname)

    def get_symbol_code(self,md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self,md5sum)
        return '%02d' % int(code.split('_')[-1])

    def get_string_code(self,string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def get_symbol_coords(self, (x1, y1, x2, y2)):
        # strip borders
        return MappedVirtKeyboard.get_symbol_coords(self, (x1+3, y1+3, x2-3, y2-3))

class LoginPage(BasePage):
    def login(self, login, pwd):
        vk = VirtKeyboard(self)

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

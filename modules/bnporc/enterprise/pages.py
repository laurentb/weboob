# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from weboob.tools.browser import BasePage
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError

import hashlib

__all__ = ['LoginPage', 'AccountsPage']


class BEPage(BasePage):
    def get_error(self):
        for title in self.document.xpath('/html/head/title'):
            if 'erreur' in title.text or 'error' in title.text:
                return self.parser.select(self.document.getroot(),
                                          '//input[@name="titre_page"]', 1, 'xpath').value


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols = {'0': '97a2b5816f2db74851fe05afd17dc9fe',
               '1': '0a24fe3a35efeb0a89aa5e7b098e6842',
               '2': '65ff550debf85eacf8efaadd6cd80aa5',
               '3': '2bd67143fcd4207ac14d0ea8afdf4ebb',
               '4': 'a46bfd21636805a31a579b253c3b23d5',
               '5': '3f644894037255bc0feaba9abb1facfa',
               '6': '40d91064a749563fa4dd31fb52e880f0',
               '7': 'cd3af65da74d57df1e6a91ca946c09b7',
               '8': '85b718e032a02e887c757a7745a1f0bd',
               '9': 'c2cdc08c8c68855d83c0899d7e8c6719',
               '-1': 'd41d8cd98f00b204e9800998ecf8427e',
               }

    color = 45

    def __init__(self, basepage):
        img = basepage.document.find("//img[@usemap='#MapGril']")
        imgdata = basepage.browser.openurl(img.attrib['src'])
        MappedVirtKeyboard.__init__(self, imgdata, basepage.document, img, self.color)
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_coords(self, (x1, y1, x2, y2)):
        # strip borders
        return MappedVirtKeyboard.get_symbol_coords(self, (x1+6, y1+1, x2-6, y2-4))

    def get_symbol_code(self, md5sum):
        code = MappedVirtKeyboard.get_symbol_code(self, md5sum)
        code = code.split("'")[1]
        assert code.isdigit()
        return code

    def get_string_code(self, string):
        code = ''
        for c in string:
            code += self.get_symbol_code(self.symbols[c])
        return code

    def checksum(self, (x1, y1, x2, y2)):
        """Copy of parent checksum(), but cropping (removes empty lines)"""
        s = ''
        for y in range(y1, min(y2 + 1, self.height)):
            for x in range(x1, min(x2 + 1, self.width)):
                if self.check_color(self.pixar[x, y]):
                    s += " "
                else:
                    s += "O"
            s += "\n"
        s = '\n'.join([l for l in s.splitlines() if l.strip()])
        #print s
        return hashlib.md5(s).hexdigest()


class LoginPage(BEPage):
    def login(self, login, password):
        try:
            vk = BNPVirtKeyboard(self)
        except VirtKeyboardError, err:
            self.logger.error("Error: %s" % err)
            return False

        self.browser.select_form(name='ident')
        self.browser.set_all_readonly(False)

        self.browser['ch1'] = login
        self.browser['chgrille'] = vk.get_string_code(password)
        self.browser.submit()


class AccountsPage(BEPage):
    pass

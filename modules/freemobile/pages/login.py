# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014  Florent Fourcot
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import time
from io import BytesIO
from PIL import Image

from weboob.browser.pages import HTMLPage


class FreeKeyboard(object):
    symbols = {'0': '001111111111110011111111111111111111111111111110000000000011110000000000011111111111111111011111111111111001111111111110',
               '1': '001110000000000001110000000000001110000000000011111111111111111111111111111111111111111111000000000000000000000000000000',
               '2': '011110000001111011110000111111111000001111111110000011110011110000111100011111111111000011011111110000011001111000000011',
               '3': '011100000011110111100000011111111000110000111110000110000011110001110000011111111111111111011111111111110001110001111100',
               '4': '000000011111000000001111111000000111110011000011110000011000111111111111111111111111111111111111111111111000000000011000',
               '5': '111111110011110111111110011111111001110000111111001100000011111001100000011111001111111111111001111111111010000111111110',
               '6': '001111111111110011111111111111111111111111111110001100000011110001100000011111001111111111111101111111111011100111111110',
               '7': '111000000000000111000000000000111000000011111111000011111111111011111111111111111111000000111111000000000111100000000000',
               '8': '001110001111110011111111111111111111111111111110000110000011110000110000011111111111111111011111111111111001111001111110',
               '9': '001111111000110011111111100111111111111100111110000001100011110000001100011111111111111111011111111111111001111111111110'
               }

    def __init__(self, basepage):
        self.basepage = basepage
        self.fingerprints = []
        for htmlimg in self.basepage.doc.xpath('//img[@class="ident_chiffre_img pointer"]'):
            url = htmlimg.attrib.get("src")
            imgfile = BytesIO(basepage.browser.open(url).content)
            img = Image.open(imgfile)
            matrix = img.load()
            s = ""
            # The digit is only displayed in the center of image
            for x in range(15, 23):
                for y in range(12, 27):
                    (r, g, b) = matrix[x, y]
                    # If the pixel is "red" enough
                    if g + b < 450:
                        s += "1"
                    else:
                        s += "0"

            self.fingerprints.append(s)

    def get_symbol_code(self, digit):
        fingerprint = self.symbols[digit]
        for i, string in enumerate(self.fingerprints):
            if string == fingerprint:
                return i
        # Image contains some noise, and the match is not always perfect
        # (this is why we can't use md5 hashs)
        # But if we can't find the perfect one, we can take the best one
        best = 0
        result = None
        for i, string in enumerate(self.fingerprints):
            match = 0
            for j, bit in enumerate(string):
                if bit == fingerprint[j]:
                    match += 1
            if match > best:
                best = match
                result = i
        self.basepage.browser.logger.debug(self.fingerprints[result] + " match " + digit)
        return result

    def get_string_code(self, string):
        code = ''
        for c in string:
            codesymbol = self.get_symbol_code(c)
            code += str(codesymbol)
        return code

    def get_small(self, string):
        for c in string:
            time.sleep(0.5)
            url = 'https://mobile.free.fr/moncompte/chiffre.php?pos=' + c + '&small=1'
            self.basepage.browser.open(url)


class LoginPage(HTMLPage):
    def login(self, login, password):
        vk = FreeKeyboard(self)
        code = vk.get_string_code(login)
        vk.get_small(code)  # If img are not downloaded, the server do not accept the login

        form = self.get_form(xpath='//form[@id="form_connect"]')
        form['login_abo'] = code
        form['pwd_abo'] = password
        form.submit()

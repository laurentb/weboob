# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot, Romain Bignon
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

from StringIO import StringIO

from weboob.tools.browser import BasePage, BrowserIncorrectPassword
from weboob.tools.captcha.virtkeyboard import VirtKeyboard
from weboob.tools.browser2.page import HTMLPage

__all__ = ['LoginPage', 'INGVirtKeyboard', 'StopPage']


class INGVirtKeyboard(VirtKeyboard):
    symbols = {'0': '327208d491507341908cf6920f26b586',
               '1': '615ff37b15645da106cebc4605b399de',
               '2': 'fb04e648c93620f8b187981f9742b57e',
               '3': 'b786d471a70de83657d57bdedb6a2f38',
               '4': '41b5501219e8d8f6d3b0baef3352ce88',
               '5': 'c72b372fb035160f2ff8dae59cd7e174',
               '6': '392fa79e9a1749f5c8c0170f6a8ec68b',
               '7': 'fb495b5cf7f46201af0b4977899b56d4',
               '8': 'e8fea1e1aa86f8fca7f771db9a1dca4d',
               '9': '82e63914f2e52ec04c11cfc6fecf7e08'
               }
    color = 64

    def __init__(self, basepage):
        self.basepage = basepage
        divkeyboard = basepage.doc.find("//div[@id='clavierdisplayLogin']")
        if divkeyboard is None:
            divkeyboard = basepage.doc.find("//div[@id='claviertransfer']")
        try:
            img = divkeyboard.xpath("img")[1]
        except:
            raise BrowserIncorrectPassword()
        url = img.attrib.get("src")
        coords = {}
        coords["11"] = (5, 5, 33, 33)
        coords["21"] = (45, 5, 73, 33)
        coords["31"] = (85, 5, 113, 33)
        coords["41"] = (125, 5, 153, 33)
        coords["51"] = (165, 5, 193, 33)
        coords["12"] = (5, 45, 33, 73)
        coords["22"] = (45, 45, 73, 73)
        coords["32"] = (85, 45, 113, 73)
        coords["42"] = (125, 45, 153, 73)
        coords["52"] = (165, 45, 193, 73)

        VirtKeyboard.__init__(self, StringIO(basepage.browser.open(url).content), coords, self.color)

        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_string_code(self, string):
        code = ''
        first = True
        for c in string:
            if not first:
                code += ","
            else:
                first = False
            codesymbol = self.get_symbol_code(self.symbols[c])
            x = (self.coords[codesymbol][0] + self.coords[codesymbol][2]) / 2
            y = (self.coords[codesymbol][1] + self.coords[codesymbol][3]) / 2
            code += str(x)
            code += ","
            code += str(y)
        return code

    def get_coordinates(self, xpath, password):
        temppasswd = ""
        span = self.basepage.doc.find(xpath)
        for i, font in enumerate(span.getiterator('font')):
            if font.attrib.get('class') == "vide":
                temppasswd += password[i]
        self.basepage.browser.logger.debug('We are looking for : ' + temppasswd)
        coordinates = self.get_string_code(temppasswd)
        self.basepage.browser.logger.debug("Coordonates: " + coordinates)
        return coordinates


class LoginPage(HTMLPage):
    def prelogin(self, login, birthday):
        # First step : login and birthday
        form = self.get_form(name='zone1Form')
        form['zone1Form:numClient'] = login
        form['zone1Form:dateDay'] = birthday[0:2]
        form['zone1Form:dateMonth'] = birthday[2:4]
        form['zone1Form:dateYear'] = birthday[4:9]
        form['zone1Form:idRememberMyCifCheck'] = False
        form.submit()

    def error(self):
        err = self.doc.find('//span[@class="error"]')
        return err is not None

    def login(self, password):
        # 2) And now, the virtual Keyboard
        vk = INGVirtKeyboard(self)

        form = self.get_form(name='mrc')
        form['mrc:mrg'] = 'mrc:mrg'
        form['AJAXREQUEST'] = '_viewRoot'
        form['mrc:mrldisplayLogin'] = vk.get_coordinates('//span[@id="digitpaddisplayLogin"]', password)
        form.submit()


class StopPage(BasePage):
    pass

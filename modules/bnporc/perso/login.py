# -*- coding: utf-8 -*-

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
from weboob.tools.mech import ClientForm
import urllib

from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.tools.captcha.virtkeyboard import MappedVirtKeyboard, VirtKeyboardError

__all__ = ['LoginPage', 'ConfirmPage', 'ChangePasswordPage']


class BNPVirtKeyboard(MappedVirtKeyboard):
    symbols={'0': '9cc4789a2cb223e8f2d5e676e90264b5',
             '1': 'e10b58fc085f9683052d5a63c96fc912',
             '2': '04ec647e7b3414bcc069f0c54eb55a4c',
             '3': 'fde84fd9bac725db8463554448f1e469',
             '4': '2359eea8671bf112b58264bec0294f71',
             '5': '82b55b63480114f04fad8c5c4fa5673a',
             '6': 'e074864faeaeabb3be3d118192cd8879',
             '7': 'af5740e4ca71fadc6f4ae1412d864a1c',
             '8': 'cab759c574038ad89a0e35cc76ab7214',
             '9': '828cf0faf86ac78e7f43208907620527'
            }

    url="/NSImgGrille?timestamp=%d"

    color=27

    def __init__(self, basepage):
        img=basepage.document.find("//img[@usemap='#MapGril']")
        MappedVirtKeyboard.__init__(self, basepage.browser.openurl(self.url % time.time()), basepage.document, img, self.color)
        self.check_symbols(self.symbols, basepage.browser.responses_dirname)

    def get_symbol_code(self, md5sum):
        code=MappedVirtKeyboard.get_symbol_code(self, md5sum)
        return code[-4:-2]

    def get_string_code(self, string):
        code=''
        for c in string:
            code+=self.get_symbol_code(self.symbols[c])
        return code


class LoginPage(BasePage):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        try:
            vk=BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s"%err)
            return False

        self.browser.select_form('logincanalnet')
        # HACK because of fucking malformed HTML, the field isn't recognized by mechanize.
        self.browser.controls.append(ClientForm.TextControl('text', 'ch1', {'value': ''}))
        self.browser.set_all_readonly(False)

        self.browser['ch1'] = login.encode('iso-8859-1')
        self.browser['ch5'] = vk.get_string_code(password)
        self.browser.submit()


class ConfirmPage(BasePage):
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


class InfoMessagePage(BasePage):
    def on_loaded(self):
        pass


class ChangePasswordPage(BasePage):
    def change_password(self, current, new):
        try:
            vk=BNPVirtKeyboard(self)
        except VirtKeyboardError as err:
            self.logger.error("Error: %s"%err)
            return False

        from mechanize import Cookie
        c = Cookie(0, 'wbo_segment_369721', 'AA%7CAB%7C%7C%7C',
                      None, False,
                      '.secure.bnpparibas.net', True, True,
                      '/', False,
                      False,
                      None,
                      False,
                      None,
                      None,
                      {})
        cookiejar = self.browser._ua_handlers["_cookies"].cookiejar

        cookiejar.set_cookie(c)

        code_current=vk.get_string_code(current)
        code_new=vk.get_string_code(new)

        data = (('ch1', code_current),
                ('ch2', code_new),
                ('radiobutton3', 'radiobutton'),
                ('ch3', code_new),
                ('x', 23),
                ('y', 13),
               )

        headers = {'Referer': self.url}
        #headers = {'Referer': "https://www.secure.bnpparibas.net/SAF_CHM?Action=SAF_CHM&Origine=SAF_CHM&stp=%s" % (int(datetime.now().strftime('%Y%m%d%H%M%S')))}
        #import time
        #time.sleep(10)
        request = self.browser.request_class('https://www.secure.bnpparibas.net/SAF_CHM_VALID', urllib.urlencode(data), headers)
        self.browser.location(request)

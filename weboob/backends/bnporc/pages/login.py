# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon
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


import re
from weboob.tools.mech import ClientForm
import urllib
from logging import error

from weboob.tools.browser import BasePage, BrowserUnavailable
from weboob.backends.bnporc.captcha import Captcha, TileError


__all__ = ['LoginPage', 'ConfirmPage', 'ChangePasswordPage']


class LoginPage(BasePage):
    def on_loaded(self):
        for td in self.document.getroot().cssselect('td.LibelleErreur'):
            if td.text is None:
                continue
            msg = td.text.strip()
            if 'indisponible' in msg:
                raise BrowserUnavailable(msg)

    def login(self, login, password):
        img = Captcha(self.browser.openurl('/NSImgGrille'))

        try:
            img.build_tiles()
        except TileError, err:
            error("Error: %s" % err)
            if err.tile:
                err.tile.display()

        self.browser.select_form('logincanalnet')
        # HACK because of fucking malformed HTML, the field isn't recognized by mechanize.
        self.browser.controls.append(ClientForm.TextControl('text', 'ch1', {'value': ''}))
        self.browser.set_all_readonly(False)

        self.browser['ch1'] = login
        self.browser['ch5'] = img.get_codes(password)
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

class MessagePage(BasePage):
    def on_loaded(self):
        pass

class ChangePasswordPage(BasePage):
    def change_password(self, current, new):
        img = Captcha(self.browser.openurl('/NSImgGrille'))

        try:
            img.build_tiles()
        except TileError, err:
            error('Error: %s' % err)
            if err.tile:
                err.tile.display()

        code_current = img.get_codes(current)
        code_new = img.get_codes(new)

        data = {'ch1': code_current,
                'ch2': code_new,
                'ch3': code_new,
                'radiobutton3': 'radiobutton',
                'x': 12,
                'y': 9,
               }

        headers = {'Referer': self.url}
        request = self.browser.request_class('https://www.secure.bnpparibas.net/SAF_CHM_VALID', urllib.urlencode(data), headers)
        self.browser.location(request)

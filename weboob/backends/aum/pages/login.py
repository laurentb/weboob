# -*- coding: utf-8 -*-

# Copyright(C) 2008-2011  Romain Bignon
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
from weboob.tools.browser import BrowserIncorrectPassword
from weboob.backends.aum.exceptions import AdopteBanned
from weboob.capabilities.account import AccountRegisterError

from .base import PageBase
from ..captcha import Captcha

class LoginPage(PageBase):
    def login(self, login, password):
        self.browser.select_form(name="form_login")
        self.browser['login'] = login
        self.browser['password'] = password

        self.browser.submit()  # submit current form

class RegisterPage(PageBase):
    def on_loaded(self):
        display_errors = False
        for div in self.document.getElementsByTagName('div'):
            if div.getAttribute('class') == 'balloon':
                display_errors = True
                break

        if not display_errors:
            return

        errors = []
        for script in self.document.getElementsByTagName('script'):
            for child in script.childNodes:
                if child and child.data.find('dispErrors') >= 0:
                    for m in re.finditer('"(\w+)": "(.*)",', child.data):
                        errors.append(m.group(2))

        raise AccountRegisterError(u'Unable to register account: %s' % ', '.join(errors))

    def register(self, password, sex, birthday_d, birthday_m, birthday_y, zipcode, country):
        """
Form name=register (#1)
## ## __Name__________________ __Type___ __ID________ __Value__________________
1     sent1time                hidden    (None)
2     sex                      radio     sex-0        [] of ['0', '1']
3     birthday0                select    birthday0    ['0'] of ['0', '1', '2', '3', '4', ' ...
4     birthday1                select    birthday1    ['0'] of ['0', '1', '2', '3', '4', ' ...
5     birthday2                select    birthday2    ['0'] of ['0', '1992', '1991', '1990 ...
6     country                  select    country      ['0'] of ['0', 'fr', 'be', 'ch', 'ca']
7     zip                      text      zip
8     email                    text      email
9     pass                     password  pass
10    pass_retype              password  pass_retype
11    captcha                  text      captcha
12    swear_adult              checkbox  swear_adult  [] of ['on']
13    want_goods               checkbox  want_goods   [] of ['on']
        """
        c = Captcha(self.browser.openurl('/captcha.php'))

        self.browser.select_form(name='register')
        self.browser.set_all_readonly(False)

        try:
            self.browser['sex'] = [str(sex)]
        except ClientForm.ItemNotFoundError:
            raise AccountRegisterError('Please give a right sex! (1 or 0)')
        try:
            self.browser['birthday0'] = [str(birthday_d)]
            self.browser['birthday1'] = [str(birthday_m)]
            self.browser['birthday2'] = [str(birthday_y)]
        except ClientForm.ItemNotFoundError:
            raise AccountRegisterError('Please give a right birthday date!')
        try:
            self.browser['country'] = [str(country)]
        except ClientForm.ItemNotFoundError:
            raise AccountRegisterError('Please select a right country!')
        self.browser['zip'] = str(zipcode)
        self.browser['email'] = self.browser.username
        self.browser['pass'] = password
        self.browser['pass_retype'] = password
        self.browser['captcha'] = c.text
        self.browser['swear_adult'] = ['on']
        self.browser['want_goods'] = []

        self.browser.submit()

class RegisterWaitPage(PageBase):
    pass

class RegisterConfirmPage(PageBase):
    pass

class RedirectPage(PageBase):
    def on_loaded(self):
        for link in self.browser.links():
            print link
        self.browser.location('/wait.php')

class BanPage(PageBase):
    def on_loaded(self):
        raise AdopteBanned('Your IP address is banned.')

class ShopPage(PageBase):
    pass

class ErrPage(PageBase):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Incorrect login/password')

class InvitePage(PageBase):
    MYID_REGEXP = re.compile("http://www.adopteunmec.com/\?mid=(\d+)")

    def get_my_id(self):
        fonts = self.document.getElementsByTagName('font')
        for font in fonts:
            m = self.MYID_REGEXP.match(font.firstChild.data)
            if m:
                return m.group(1)

        self.browser.logger.error("Error: Unable to find my ID")
        return 0

# -*- coding: utf-8 -*-

"""
Copyright(C) 2008-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backends.aum.pages.base import PageBase
from weboob.tools.browser import BrowserIncorrectPassword

class LoginPage(PageBase):
    def login(self, login, password):
        self.browser.select_form(name="form_login")
        self.browser['login'] = login
        self.browser['password'] = password

        self.browser.submit()  # submit current form

class RegisterPage(PageBase):
    def register(self, nickname, password, sex, birthday_d, birthday_m, birthday_y, zipcode, country, godfather):
        """ form2:
              - pseudo
              - email
              - password
              - sex (0=m, 1=f)
              - birthday0 (0-31)
              - birthday1 (0-12)
              - birthday2 (1930-1999)
              - zip
              - country (fr,be,ch,ca)
              - godfather
        """
        self.browser.select_form(name="form2")
        self.browser.controls.pop() # pop the 'sex' control which is twice on page
        self.browser.set_all_readonly(False)

        if isinstance(nickname, unicode):
            nickname = nickname.encode('iso-8859-15', 'ignore')
        self.browser['pseudo'] = nickname
        self.browser['email'] = self.browser.username
        self.browser['pass'] = password
        self.browser['sex0'] = [str(sex)]
        self.browser['sex'] = str(sex)
        self.browser['birthday0'] = [str(birthday_d)]
        self.browser['birthday1'] = [str(birthday_m)]
        self.browser['birthday2'] = [str(birthday_y)]
        self.browser['zip'] = str(zipcode)
        self.browser['country'] = [str(country)]
        self.browser['godfather'] = godfather

        self.browser.submit()

class RegisterWaitPage(PageBase):
    pass

class RegisterConfirmPage(PageBase):
    pass

class RedirectPage(PageBase):
    def loaded(self):
        for link in self.browser.links():
            print link
        self.browser.location('/wait.php')

class BanPage(PageBase):
    pass

class ShopPage(PageBase):
    pass

class ErrPage(PageBase):
    def loaded(self):
        raise BrowserIncorrectPassword('Incorrect login/password')

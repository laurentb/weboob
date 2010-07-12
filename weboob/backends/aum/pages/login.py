# -*- coding: utf-8 -*-

# Copyright(C) 2008-2010  Romain Bignon
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from weboob.backends.aum.pages.base import PageBase
from weboob.tools.browser import BrowserIncorrectPassword

class LoginPage(PageBase):
    def login(self, login, password):
        self.browser.select_form(name="form_login")
        self.browser['login'] = login
        self.browser['password'] = password

        self.browser.submit()  # submit current form

class RegisterPage(PageBase):
    def register(self, password, sex, birthday_d, birthday_m, birthday_y, zipcode, country, captcha):
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
        self.browser.select_form(name='register')
        self.browser.set_all_readonly(False)

        self.browser['sex'] = str(sex)
        self.browser['birthday0'] = [str(birthday_d)]
        self.browser['birthday1'] = [str(birthday_m)]
        self.browser['birthday2'] = [str(birthday_y)]
        self.browser['country'] = [str(country)]
        self.browser['zip'] = str(zipcode)
        self.browser['email'] = self.browser.username
        self.browser['pass'] = password
        self.browser['pass_retype'] = password
        self.browser['captcha'] = captcha
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
    pass

class ShopPage(PageBase):
    pass

class ErrPage(PageBase):
    def on_loaded(self):
        raise BrowserIncorrectPassword('Incorrect login/password')

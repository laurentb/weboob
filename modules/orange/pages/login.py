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

from weboob.deprecated.browser import Page
from weboob.tools.compat import urlencode

class LoginPage(Page):
    def on_loaded(self):
        pass

    def login(self, user, pwd):
        post_data = {"credential" : str(user),
                     "password" : str(pwd),
                     "save_user": "false",
                     "save_pwd" : "false",
                     "save_TC"  : "true",
                     "action"   : "valider",
                     "usertype" : "",
                     "service"  : "",
                     "url"      : "http://www.orange.fr",
                     "case"     : "",
                     "origin"   : "",    }

        post_data = urlencode(post_data)
        self.browser.addheaders = [('Referer', 'http://id.orange.fr/auth_user/template/auth0user/htm/vide.html'),
                              ("Content-Type" , 'application/x-www-form-urlencoded') ]

        self.browser.open(self.browser.geturl(), data=post_data)

        #~ print "LOGIN!!!"
        #~ self.browser.select_form(predicate=lambda form: "id" in form.attrs and form.attrs["id"] == "authentication_form" )
        #~ user_control = self.browser.find_control(id="user_credential")
        #~ user_control.value = user
        #~ pwd_control = self.browser.find_control(id="user_password")
        #~ pwd_control.value = pwd
        #~ self.browser.submit()

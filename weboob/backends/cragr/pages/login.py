# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

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

import ClientForm

from .base import CragrBasePage

class LoginPage(CragrBasePage):
    def loaded(self):
        pass

    def login(self, login, password):
        self.browser.select_form(nr=0)
        print self.browser.controls
        try:
            self.browser['numero'] = login
            self.browser['code'] = password
        except ClientForm.ControlNotFoundError:
            try:
                self.browser['userLogin'] = login
                self.browser['userPassword'] = password
            except ClientForm.ControlNotFoundError, e:
                print 'WTF', e
                self.browser.controls.append(ClientForm.TextControl('text', 'userLogin', {'value': ''}))
                self.browser.controls.append(ClientForm.TextControl('text', 'userPassword', {'value': ''}))
                self.browser.set_all_readonly(False)
                self.browser['userLogin'] = login
                self.browser['userPassword'] = password

        self.browser.submit()

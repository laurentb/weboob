# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from weboob.deprecated.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError

from .base import CragrBasePage


class LoginPage(CragrBasePage):
    def login(self, login, password):
        self.browser.select_form(nr=0)
        self.browser.set_all_readonly(False)
        try:
            self.browser['numero'] = login
            self.browser['code'] = password
        except ControlNotFoundError:
            try:
                self.browser['userLogin'] = login
                self.browser['userPassword'] = password
            except ControlNotFoundError:
                self.browser.controls.append(ClientForm.TextControl('text', 'numero', {'value': ''}))
                self.browser.controls.append(ClientForm.TextControl('text', 'code', {'value': ''}))
                self.browser.controls.append(ClientForm.TextControl('text', 'userLogin', {'value': ''}))
                self.browser.controls.append(ClientForm.TextControl('text', 'userPassword', {'value': ''}))
                self.browser['numero'] = login
                self.browser['code'] = password
                self.browser['userLogin'] = login
                self.browser['userPassword'] = password

        self.browser.submit()

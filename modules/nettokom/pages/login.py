# -*- coding: utf-8 -*-

# Copyright(C) 2012  Florent Fourcot
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


class LoginPage(Page):
    def on_loaded(self):
        pass

    def login(self, login, password):
        self.browser.select_form(nr=0)
        self.browser.set_all_readonly(False)
        self.browser['number'] = login.encode('iso-8859-1')
        self.browser['password'] = password.encode('iso-8859-1')
        self.browser.submit(nologin=True)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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
    def login(self, login, password):
        self.browser.select_form(nr=0)
        self.browser['username'] = login
        self.browser['password'] = password
        self.browser['remember-me'] = ['on']
        self.browser.submit()

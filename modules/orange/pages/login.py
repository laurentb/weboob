# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Vincent Paredes
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.tools.json import json
from weboob.browser.filters.standard import CleanText, Format


class LoginPage(HTMLPage):
    def login(self, username, password):
        json_data = {
            'login': username,
            'mem': False,
        }
        response = self.browser.location('https://login.orange.fr/front/login', json=json_data)

        json_data = {
            'login': username,
            'password': password,
            'loginEncrypt': json.loads(response.json()['options'])['loginEncrypt']
        }
        self.browser.location('https://login.orange.fr/front/password', json=json_data)


class ManageCGI(HTMLPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    def get_error_message(self):
        return Format('%s %s', CleanText('//div[has-class("modal-dialog")]//h3'), CleanText('//div[has-class("modal-dialog")]//p[1]'))(self.doc)

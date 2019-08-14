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

from __future__ import unicode_literals

import lxml.html as html

from StringIO import StringIO

from weboob.browser.pages import HTMLPage, LoggedPage, JsonPage
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


class PasswordPage(JsonPage):
    def get_change_password_message(self):
        if self.doc.get('stage') != 'changePassword':
            # when stage is not present everything is okay, and if it's not changePassword we prefer do nothing here
            return

        if 'mandatory' not in self.doc['options']:
            # maybe there are some cases where it's optional
            return

        encoding = self.encoding
        if encoding == 'latin-1':
            encoding = 'latin1'
        if encoding:
            encoding = encoding.replace('ISO8859_', 'ISO8859-')

        parser = html.HTMLParser(encoding=encoding)
        html_doc = html.parse(StringIO(self.doc['view']), parser)

        # message should be:
        # Votre mot de passe actuel n’est pas suffisamment sécurisé et doit être renforcé.
        # Veuillez le modifier pour accéder à vos services Orange.
        return CleanText('//p[@id="cnMsg"]')(html_doc)


class ManageCGI(HTMLPage):
    pass


class HomePage(LoggedPage, HTMLPage):
    def get_error_message(self):
        return Format('%s %s', CleanText('//div[has-class("modal-dialog")]//h3'), CleanText('//div[has-class("modal-dialog")]//p[1]'))(self.doc)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from weboob.tools.browser import BasePage


__all__ = ['LoginPage']


class LoginPage(BasePage):
    def on_loaded(self):
        pass
#        for td in self.document.getroot().cssselect('td.LibelleErreur'):
#            if td.text is None:
#                continue
#            msg = td.text.strip()
#            if 'indisponible' in msg:
#                raise BrowserUnavailable(msg)

    def login(self, login, password):
        DOMAIN = self.browser.DOMAIN

        url_login = 'https://' + DOMAIN + '/connexion.phtml'

        self.browser.openurl(url_login)
        self.browser.select_form('identification')
        self.browser.set_all_readonly(False)

        self.browser['login'] = login
        self.browser['password'] = password
        self.browser.submit()

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Tony Malto
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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AccountsPage


class GmfBrowser(LoginBrowser):
    BASEURL = 'http://www.gmf.com'

    login = URL(r'https://espace-assure.gmf.fr/public/pages/securite/IC2.faces', LoginPage)
    accounts = URL(r'https://espace-assure.gmf.fr/pointentree/client/homepage', AccountsPage)

    def do_login(self):
        self.login.go().login(self.username, self.password)
        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def iter_accounts(self):
        return self.accounts.stay_or_go().iter_accounts()

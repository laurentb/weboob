# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, ProfilPage, DocumentsPage


class OnlinenetBrowser(LoginBrowser):
    BASEURL = 'https://console.online.net/en/'
    TIMEOUT = 60

    login = URL('login', LoginPage)
    profil = URL('account/edit', ProfilPage)
    documents = URL('bill/list', DocumentsPage)

    def do_login(self):
        self.login.go()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_subscription_list(self):
        return self.profil.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        for b in self.documents.stay_or_go().get_bills():
            yield b
        for d in self.documents.stay_or_go().get_documents():
            yield d

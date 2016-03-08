# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, ProfilPage, DocumentsPage


class MaterielnetBrowser(LoginBrowser):
    BASEURL = 'https://www.materiel.net/'

    login = URL('pm/client/login.html', LoginPage)
    profil = URL('pm/client/compte.html', ProfilPage)
    documents = URL('pm/client/commande.html\?page=(?P<page>.*)',
                    'pm/client/commande.html', DocumentsPage)

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
        return self.documents.stay_or_go(page=1).get_documents()

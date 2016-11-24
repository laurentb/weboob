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


class EdfBrowser(LoginBrowser):
    BASEURL = 'https://particulier.edf.fr'

    login = URL('/bin/edf_rc/servlets/authentication', LoginPage)
    profil = URL('/services/rest/authenticate/getListContracts', ProfilPage)
    documents = URL('https://monagencepart.edf.fr/ASPFront/appmanager/ASPFront/front\?service=page_mes_factures&privee=true&accord=(?P<subid>\d+)',
                    'https://monagencepart.edf.fr', DocumentsPage)

    def do_login(self):
        self.location(self.BASEURL)

        data = {'login': self.username, 'password': self.password}
        self.login.go(data=data)

        if not self.page.is_logged():
            raise BrowserIncorrectPassword

    @need_login
    def get_subscription_list(self):
        return self.profil.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        return self.documents.stay_or_go(subid=subscription.id).get_documents(subid=subscription.id)

    @need_login
    def download_document(self, document):
        return self.open(document.url).content

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Juliette Fourcot
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


from weboob.browser import LoginBrowser, need_login, URL
from weboob.browser.profiles import Firefox
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.base import find_object
from weboob.capabilities.bill import DocumentNotFound
from .pages import LoginPage, DocumentsPage, HomePage, LoginControlPage,\
                   LoginValidityPage, ListYear


class EnsapBrowser(LoginBrowser):
    BASEURL = 'https://ensap.gouv.fr'
    PROFILE = Firefox()

    loginp = URL('/web/views/contenus/accueilnonconnecte.html', LoginPage)
    loginvalidity = URL('/authentification', LoginValidityPage)
    authp = URL('/prive/initialiserhabilitation/v1', LoginControlPage)
    homep = URL('/prive/accueilconnecte/v1', HomePage)
    documents = URL('/prive/remuneration/v1/(?P<year>\d+)', DocumentsPage)
    listyears = URL('/prive/listeanneeremuneration/v1', ListYear)
    logged = False
    token = None

    def do_login(self):
        self.logger.debug('call Browser.do_login')
        if self.logged:
            return True

        self.loginp.stay_or_go()
        self.loginvalidity.go(data={"identifiant": self.username,
                                    "secret": self.password})
        if not self.page.check_logged():
            raise BrowserIncorrectPassword()
        self.authp.go(data="{}", headers={'Content-Type': 'application/json'})
        self.token = self.page.get_xsrf()
        self.logged = True

    @need_login
    def iter_documents(self, subscription):
        self.listyears.go()
        years = self.page.get_years()
        # use reverse order of list to get recent documents first
        for year in years[::-1]:
            self.documents.stay_or_go(year=year, headers={"X-XSRF-TOKEN": self.token})
            self.token = self.session.cookies.get("XSRF-TOKEN")
            for doc in self.page.iter_documents():
                yield doc

    @need_login
    def iter_subscription(self):
        self.homep.stay_or_go(headers={"X-XSRF-TOKEN": self.token})
        self.token = self.session.cookies.get("XSRF-TOKEN")
        return self.page.iter_subscription()

    @need_login
    def get_document(self, id):
        return find_object(self.iter_documents(None), id=id,
                           error=DocumentNotFound())

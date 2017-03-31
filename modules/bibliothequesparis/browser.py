# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from .pages import LoginPage, LoansPage


class BibliothequesparisBrowser(LoginBrowser):
    BASEURL = 'https://bibliotheques.paris.fr/'

    login = URL(r'/Default/Portal/Recherche/logon.svc/logon', LoginPage)
    bookings = URL('/Default/Portal/Recherche/Search.svc/RenderAccountWebFrame', LoansPage)

    def do_login(self):
        d = {
            'username': self.username,
            'password': self.password,
        }
        self.login.go(data=d)

    @property
    def json_headers(self):
        return {
            'Accept': 'application/json, text/javascript',
            'Content-Type': 'application/json; charset=utf-8',
        }

    @need_login
    def get_loans(self):
        # do not add any space! the site is so fragile it breaks if even a single whitespace is added...
        s = '{"portalId":5,"category":"Loans","providerCode":""}'
        self.session.cookies['ErmesSearch_Default'] = '{"mainScenario":"CATALOGUE","mainScenarioText":"Catalogue"}'
        self.bookings.go(data=s, headers=self.json_headers)
        return self.page.sub.get_loans()

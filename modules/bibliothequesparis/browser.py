# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object

from .pages import LoginPage, LoansPage, RenewPage, SearchPage


class BibliothequesparisBrowser(LoginBrowser):
    BASEURL = 'https://bibliotheques.paris.fr/'

    login = URL(r'/Default/Portal/Recherche/logon.svc/logon', LoginPage)
    bookings = URL('/Default/Portal/Recherche/Search.svc/RenderAccountWebFrame', LoansPage)
    renew = URL(r'/Default/Portal/Services/ILSClient.svc/RenewLoans', RenewPage)
    search = URL(r'/Default/Portal/Recherche/Search.svc/Search', SearchPage)

    json_headers = {
        'Accept': 'application/json, text/javascript',
        'Content-Type': 'application/json; charset=utf-8',
    }

    def do_login(self):
        d = {
            'username': self.username,
            'password': self.password,
        }
        self.login.go(data=d, headers={'Accept': 'application/json, text/javascript'})

    @need_login
    def get_loans(self):
        # do not add any space! the site is so fragile it breaks if even a single whitespace is added...
        s = '{"portalId":5,"category":"Loans","providerCode":""}'
        self.session.cookies['ErmesSearch_Default'] = '{"mainScenario":"CATALOGUE","mainScenarioText":"Catalogue"}'
        self.bookings.go(data=s, headers=self.json_headers)
        return self.page.sub.get_loans()

    @need_login
    def do_renew(self, id):
        b = find_object(self.get_loans(), id=id)
        assert b, 'loan not found'
        assert b._renew_data, 'book has no data'
        post = u'{"loans":[%s]}' % b._renew_data
        self.renew.go(data=post.encode('utf-8'), headers=self.json_headers)

    def search_books(self, pattern):
        max_page = 0
        page = 0
        while page <= max_page:
            d = {
                "query": {
                    "Page": page,
                    "PageRange": 3,
                    "QueryString": pattern,
                    "ResultSize": 50,
                    "ScenarioCode": "CATALOGUE",
                    "SearchContext": 0,
                    "SearchLabel": "",
                    "Url": "https://bibliotheques.paris.fr/Default/search.aspx?SC=CATALOGUE&QUERY={q}&QUERY_LABEL=#/Search/(query:(Page:{page},PageRange:3,QueryString:{q},ResultSize:50,ScenarioCode:CATALOGUE,SearchContext:0,SearchLabel:''))".format(q=pattern, page=page),
                }
            }
            self.location('/Default/Portal/Recherche/Search.svc/Search', json=d, headers=self.json_headers)
            for book in self.page.iter_books():
                yield book

            max_page = self.page.get_max_page()
            page += 1

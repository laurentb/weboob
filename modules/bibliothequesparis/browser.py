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

from time import time

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object

from .pages import LoginPage, LoansPage, RenewPage, SearchPage


class BibliothequesparisBrowser(LoginBrowser):
    BASEURL = 'https://bibliotheques.paris.fr/'

    login = URL(r'/Default/Portal/Recherche/logon.svc/logon', LoginPage)
    bookings = URL(r'/Default/Portal/Services/UserAccountService.svc/ListLoans\?serviceCode=SYRACUSE&token=(?P<ts>\d+)&userUniqueIdentifier=&timestamp=(?P<ts2>\d+)', LoansPage)

    renew = URL(r'/Default/Portal/Services/UserAccountService.svc/RenewLoans', RenewPage)
    search = URL(r'/Default/Portal/Recherche/Search.svc/Search', SearchPage)

    json_headers = {
        'Accept': 'application/json, text/javascript',
    }

    def do_login(self):
        d = {
            'username': self.username,
            'password': self.password,
        }
        self.login.go(data=d, headers={'Accept': 'application/json, text/javascript'})

    @need_login
    def get_loans(self):
        now = int(time() * 1000)
        self.bookings.go(ts=now, ts2=now, headers=self.json_headers)
        return self.page.get_loans()

    @need_login
    def do_renew(self, id):
        b = find_object(self.get_loans(), id=id)
        assert b, 'loan not found'
        assert b._renew_data, 'book has no data'
        post = {
            'loans': [b._renew_data],
            'serviceCode': 'SYRACUSE',
            'userUniqueIdentifier': '',
        }
        self.renew.go(json=post, headers=self.json_headers)
        self.page.check_error()

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

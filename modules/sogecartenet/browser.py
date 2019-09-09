# -*- coding: utf-8 -*-

# Copyright(C) 2015 Budget Insight
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


from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta

from weboob.tools.compat import basestring
from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.compat import urlparse, parse_qs, urlencode, urlunparse

from .pages import LoginPage, AccountsPage, TransactionsPage, PassModificationPage


class SogecartesBrowser(LoginBrowser):
    BASEURL = 'https://www.sogecartenet.fr/'

    login = URL('/internationalisation/identification', LoginPage)
    pass_modification = URL('/internationalisation/./modificationMotPasse.*', PassModificationPage)
    accounts = URL('/internationalisation/gestionParcCartes', AccountsPage)
    transactions = URL('/internationalisation/csv/operationsParCarte.*', TransactionsPage)

    EMPTY_MONTHS_LIMIT_TRANSACTIONS = 3
    MAX_MONTHS_TRANSACTIONS = 48

    def load_state(self, state):
        pass

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        data = {"USER": self.username,
                "PWD": self.password[:10],
                "ACCES": "PE",
                "LANGUE": "en",
                "QUEFAIRE": "LOGIN",
                }
        self.login.go(data=data)

    @need_login
    def iter_accounts(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def get_history(self, account):
        if not account._url:
            return

        url = account._url
        months_without_data = 0
        total_months = 0
        # If it makes more than 3 months that we get empty data or if it makes more than 48 months
        # that we are gathering transactions we stop asking for transactions (the 48 months limit is
        # just to avoid infinite loops)
        while months_without_data < self.EMPTY_MONTHS_LIMIT_TRANSACTIONS and total_months < self.MAX_MONTHS_TRANSACTIONS:
            self.location(url)
            assert self.transactions.is_here()
            if self.page.has_data():
                months_without_data = 0
                for tr in self.page.get_history():
                    yield tr
            else:
                months_without_data += 1

            # We change the end of the url by the previous month
            # URL is like this : https://www.sogecartenet.fr/csv/operationsParCarte?TOP=1&NOCARTE=XXXXXXXXX&NOCONTRAT=XXXXXXXX&DATEARR=2019-10-01
            # Format of the date in the URL is : YYYY-MM-DD
            parts = urlparse(url)
            qs = parse_qs(parts.query)
            tr_date = parse_date(qs['DATEARR'][0], yearfirst=True) - relativedelta(months=1)
            qs['DATEARR'] = tr_date.date()
            url = urlunparse(
                parts._replace(
                    query=urlencode(qs, doseq=True)
                )
            )
            total_months += 1

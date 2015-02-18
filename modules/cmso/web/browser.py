# -*- coding: utf-8 -*-

# Copyright(C) 2014      smurail
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


import datetime
from dateutil.relativedelta import relativedelta
from itertools import chain

from weboob.exceptions import BrowserHTTPError, BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.tools.date import LinearDateGuesser

from .pages import LoginPage, AccountsPage, HistoryPage


class CmsoProBrowser(LoginBrowser):
    BASEURL = 'https://www.cmso.com/'

    login = URL('/banque/assurance/credit-mutuel/pro/accueil\?espace=professionnels', LoginPage)
    subscription = URL('/domiweb/prive/espacesegment/selectionnerAbonnement/0-selectionnerAbonnement.act')
    accounts = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/0-situationGlobaleProfessionnel.act', AccountsPage)
    history = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/1-situationGlobaleProfessionnel.act', HistoryPage)

    def do_login(self):
        self.login.stay_or_go()
        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPError as e:
            # Yes, I know... In the Wild Wild Web, nobody respects nothing
            if e.response.status_code == 500:
                raise BrowserIncorrectPassword()
            else:
                raise
        else:
            self.subscription.go()

    @need_login
    def get_accounts_list(self):
        self.accounts.go()
        return self.page.iter_accounts()

    @need_login
    def get_history(self, account):
        if account._history_url.startswith('javascript:'):
            raise NotImplementedError()

        # Query history for 6 last months
        def format_date(d):
            return datetime.date.strftime(d, '%d/%m/%Y')
        today = datetime.date.today()
        period = (today - relativedelta(months=6), today)
        query = {'date': ''.join(map(format_date, period))}

        # Let's go
        self.location(account._history_url)
        first_page = self.page
        rest_page = self.history.go(data=query)

        date_guesser = LinearDateGuesser()

        return chain(first_page.iter_history(date_guesser=date_guesser), reversed(list(rest_page.iter_history(date_guesser=date_guesser))))

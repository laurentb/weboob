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
from weboob.browser.exceptions import ServerError
from weboob.tools.date import LinearDateGuesser

from .pages import LoginPage, AccountsPage, HistoryPage, ChoiceLinkPage, SubscriptionPage, InvestmentPage, InvestmentAccountPage, UselessPage


class CmsoProBrowser(LoginBrowser):
    login = URL('/banque/assurance/credit-mutuel/pro/accueil\?espace=professionnels', LoginPage)
    choice_link = URL('/domiweb/accueil.jsp', ChoiceLinkPage)
    subscription = URL('/domiweb/prive/espacesegment/selectionnerAbonnement/0-selectionnerAbonnement.act', SubscriptionPage)
    accounts = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/0-situationGlobaleProfessionnel.act', AccountsPage)
    history = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/1-situationGlobaleProfessionnel.act', HistoryPage)
    useless = URL('/domiweb/prive/particulier/modificationMotDePasse/0-expirationMotDePasse.act', UselessPage)

    investment = URL('/domiweb/prive/particulier/portefeuilleSituation/0-situationPortefeuille.act', InvestmentPage)
    invest_account = URL(r'/domiweb/prive/particulier/portefeuilleSituation/2-situationPortefeuille.act\?(?:csrf=[^&]*&)?indiceCompte=(?P<idx>\d+)&idRacine=(?P<idroot>\d+)', InvestmentAccountPage)

    def __init__(self, website, *args, **kwargs):
        super(CmsoProBrowser, self).__init__(*args, **kwargs)
        self.BASEURL = "https://www.%s" % website
        self.areas = None

    def do_login(self):
        self.login.stay_or_go()
        try:
            self.page.login(self.username, self.password)
        except BrowserHTTPError as e:
            # Yes, I know... In the Wild Wild Web, nobody respects nothing
            if e.response.status_code in (500, 401):
                raise BrowserIncorrectPassword()
            else:
                raise
        self.fetch_areas()

    def fetch_areas(self):
        if self.areas is None:
            self.subscription.go()
            self.areas = list(self.page.get_areas())

    @need_login
    def iter_accounts(self):
        self.fetch_areas()

        # Manage multiple areas
        if not self.areas:
            raise BrowserIncorrectPassword("Vous n'avez pas de comptes sur l'espace professionnel de ce site.")
        for area in self.areas:
            self.subscription.stay_or_go()
            self.location(area)
            try:
                for a in self.accounts.go().iter_accounts():
                    a._area = area
                    yield a
            except ServerError:
                self.logger.warning('Area not unavailable.')

    @need_login
    def iter_history(self, account):
        self.fetch_areas()

        if account._history_url.startswith('javascript:'):
            raise NotImplementedError()

        # Manage multiple areas
        self.subscription.go()
        self.location(account._area)
        self.accounts.go()

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

    @need_login
    def iter_coming(self, account):
        raise NotImplementedError()

    @need_login
    def iter_investment(self, account):
        self.fetch_areas()

        self.subscription.go()
        self.location(account._area)

        self.investment.go()
        assert self.investment.is_here()
        for page_account in self.page.iter_accounts():
            if page_account.id == account.id:
                if page_account._formdata:
                    self.page.go_account(*page_account._formdata)
                else:
                    self.location(page_account.url)
                break
        else:
            # not an investment account
            return []

        if self.investment.is_here():
            assert self.page.has_error()
            self.logger.warning('account %r does not seem to be usable', account)
            return []

        assert self.invest_account.is_here()
        invests = list(self.page.iter_investments())
        assert len(invests) < 2, 'implementation should be checked with more than 1 investment' # FIXME
        return invests

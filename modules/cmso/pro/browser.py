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
import re

from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import Account
from weboob.exceptions import BrowserHTTPError, BrowserIncorrectPassword, ActionNeeded
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError
from weboob.tools.date import LinearDateGuesser

from .pages import (
    LoginPage, PasswordCreationPage, AccountsPage, HistoryPage, ChoiceLinkPage, SubscriptionPage, InvestmentPage,
    InvestmentAccountPage, UselessPage, TokenPage, SSODomiPage, AuthCheckUser, SecurityCheckUser,
)

from ..par.pages import ProfilePage
from ..par.browser import CmsoParBrowser


class CmsoProBrowser(LoginBrowser):
    login = URL('/banque/assurance/credit-mutuel/pro/accueil\?espace=professionnels', LoginPage)
    choice_link = URL('/domiweb/accueil.jsp', ChoiceLinkPage)
    subscription = URL('/domiweb/prive/espacesegment/selectionnerAbonnement/0-selectionnerAbonnement.act', SubscriptionPage)
    accounts = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/0-situationGlobaleProfessionnel.act', AccountsPage)
    history = URL('/domiweb/prive/professionnel/situationGlobaleProfessionnel/1-situationGlobaleProfessionnel.act', HistoryPage)
    password_creation = URL('/domiweb/prive/particulier/modificationMotDePasse/0-creationMotDePasse.act', PasswordCreationPage)
    useless = URL('/domiweb/prive/particulier/modificationMotDePasse/0-expirationMotDePasse.act', UselessPage)

    investment = URL('/domiweb/prive/particulier/portefeuilleSituation/0-situationPortefeuille.act', InvestmentPage)
    invest_account = URL(r'/domiweb/prive/particulier/portefeuilleSituation/2-situationPortefeuille.act\?(?:csrf=[^&]*&)?indiceCompte=(?P<idx>\d+)&idRacine=(?P<idroot>\d+)', InvestmentAccountPage)

    profile = URL('https://pro.(?P<website>[\w.]+)/domiapi/oauth/json/edr/infosPerson', ProfilePage)

    tokens = URL('/domiweb/prive/espacesegment/selectionnerAbonnement/3-selectionnerAbonnement.act', TokenPage)
    ssoDomiweb = URL('https://pro.(?P<website>[\w.]+)/domiapi/oauth/json/ssoDomiwebEmbedded', SSODomiPage)
    auth_checkuser = URL('https://pro.(?P<website>[\w.]+)/auth/checkuser', AuthCheckUser)
    security_checkuser = URL('https://pro.(?P<website>[\w.]+)/securityapi/checkuser', SecurityCheckUser)

    def __init__(self, website, *args, **kwargs):
        super(CmsoProBrowser, self).__init__(*args, **kwargs)

        # Arkea Banque Privee uses a specific URL prefix
        if website == 'arkeabanqueprivee.fr':
            self.BASEURL = "https://m.%s" % website
        else:
            self.BASEURL = "https://mon.%s" % website

        self.BASEURL = "https://www.%s" % website
        self.website = website
        self.areas = None
        self.arkea = CmsoParBrowser.ARKEA[website]
        self.csrf = None
        self.last_csrf = None
        self.token = None

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

        if self.useless.is_here():
            # user didn't change his password for 6 months and website ask us if we want to change it
            # just skip it by calling this url
            self.location('/domiweb/accueil.jsp', method='POST')

        if self.password_creation.is_here():
            # user got a temporary password and never changed it, website ask to set a new password before grant access
            raise ActionNeeded(self.page.get_message())

        self.fetch_areas()

    def fetch_areas(self):
        if self.areas is None:
            self.subscription.stay_or_go()
            self.areas = list(self.page.get_areas())

    def go_with_ssodomi(self, path):
        if isinstance(path, URL):
            path = path.urls[0]
        if path.startswith('/domiweb'):
            path = path[len('/domiweb'):]

        url = self.ssoDomiweb.go(website=self.website,
                                 headers={'Authentication': 'Bearer %s' % self.token,
                                          'Authorization': 'Bearer %s' % self.csrf,
                                          'X-Csrf-Token': self.csrf,
                                          'Accept': 'application/json',
                                          'X-REFERER-TOKEN': 'RWDPRO',
                                          'X-ARKEA-EFS': self.arkea,
                                          'ADRIM': 'isAjax:true',
                                          },
                                 json={'rwdStyle': 'true',
                                       'service': path}).get_sso_url()
        page = self.location(url).page
        # each time we get a new csrf we store it because it can be used in further navigation
        self.last_csrf = self.url.split('csrf=')[1]
        return page

    def go_on_area(self, area):
        #self.subscription.stay_or_go()
        if not self.subscription.is_here():
            self.go_with_ssodomi(self.subscription)

        area = re.sub(r'csrf=(\w+)', 'csrf=' + self.page.get_csrf(), area)
        self.logger.info('Go on area %s', area)
        self.location(area)
        self.location('/domiweb/accueil.jsp')
        self.auth_checkuser.go(website=self.website)
        self.security_checkuser.go(
            website=self.website,
            json={'appOrigin': 'domiweb', 'espaceApplication': 'PRO'},
            headers={'Authentication': 'Bearer %s' % self.token,
                     'Authorization': 'Bearer %s' % self.csrf,
                     'X-Csrf-Token': self.csrf,
                     'Accept': 'application/json',
                     'X-REFERER-TOKEN': 'RWDPRO',
                     'X-ARKEA-EFS': self.arkea,
                     'ADRIM': 'isAjax:true',
                     })

    @need_login
    def iter_accounts(self):
        self.fetch_areas()

        # Manage multiple areas
        if not self.areas:
            raise BrowserIncorrectPassword("Vous n'avez pas de comptes sur l'espace professionnel de ce site.")

        seen = set()
        for area in self.areas:
            self.go_on_area(area)
            try:
                account_page = self.go_with_ssodomi(self.accounts)
                for a in account_page.iter_accounts():

                    if a.type == Account.TYPE_MARKET:
                        # for legacy reason we have to get id on investment page for market account
                        account_page = self.go_with_ssodomi(self.investment)
                        assert self.investment.is_here()

                        for inv_account in self.page.iter_accounts():
                            if self._match_account_ids(a.id, inv_account.id):
                                a.id = inv_account.id
                                break

                    seenkey = (a.id, a._owner)
                    if seenkey in seen:
                        self.logger.warning('skipping seemingly duplicate account %r', a)
                        continue

                    a._area = area
                    seen.add(seenkey)
                    yield a
            except ServerError:
                self.logger.warning('Area not unavailable.')

    def _build_next_date_range(self, date_range):
        date_format = '%d/%m/%Y'
        last_day = datetime.datetime.strptime(date_range[10:], date_format)
        first_day = last_day + datetime.timedelta(days=1)
        last_day = first_day + relativedelta(months=1, days=-1)
        return ''.join((datetime.datetime.strftime(first_day, date_format), datetime.datetime.strftime(last_day, date_format)))

    @need_login
    def iter_history(self, account):
        if account._history_url.startswith('javascript:') or account._history_url == '#':
            raise NotImplementedError()

        account = find_object(self.iter_accounts(), id=account.id)
        # this url (reached with a GET) return some transactions, but not in same format than POST method
        # and some transactions are duplicated and other are missing, don't take them from GET
        # because we don't want to manage both way in iter_history

        # fetch csrf token
        self.go_with_ssodomi(self.accounts)
        # we have to update the url at this moment because history consultation has to follow immediatly accounts page consultation.
        account._history_url = self.update_csrf_token(account._history_url)

        self.location(account._history_url)
        date_range_list = self.page.get_date_range_list()

        # a date_range is a couple of date like '01/03/201831/03/2018' but current month is often missing and we have to rebuild it
        # from first one to get very recent transaction without scrap them from 1st page (reached with GET url)
        if len(date_range_list):
            date_range_list = [self._build_next_date_range(date_range_list[0])] + date_range_list


        for date_range in date_range_list:
            date_guesser = LinearDateGuesser(datetime.datetime.strptime(date_range[10:], "%d/%m/%Y"))
            try:
                self.location(account._history_url, data={'date': date_range})
            except ServerError as error:
                if error.response.status_code == 500:
                    if 'RELEVE NON DISPONIBLE A CETTE PERIODE' in error.response.text:
                        continue
                        # just skip because it's still possible to have transactions next months
                        # Yes, they really did that heresy...
                    else:
                        raise
            for tr in sorted_transactions(self.page.iter_history(date_guesser=date_guesser)):
                yield tr

    def update_csrf_token(self, history_url):
        return re.sub('(?<=csrf=)[0-9a-zA-Z]+', self.last_csrf, history_url)

    @need_login
    def iter_coming(self, account):
        raise NotImplementedError()

    def _match_account_ids(self, account_page_id, investment_page_id):
        # account id in investment page, is a little bit different from the account page
        # some part of id have swapped and one other (with two digit) is not present
        # if account_page_id is 222223333311111111144 then investment_page_id will be 111111111.33333xx
        number, _id = investment_page_id.split('.')
        _id = _id[:-2] + number

        return _id in account_page_id

    @need_login
    def iter_investment(self, account):
        self.go_on_area(account._area)

        self.go_with_ssodomi(self.investment)
        assert self.investment.is_here()
        for page_account in self.page.iter_accounts():
            if account.id == page_account.id:
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

    @need_login
    def get_profile(self):
        self.go_on_area(self.areas[0])
        # this code is copied from CmsoParBrowser
        if self.token is None:
            self.tokens.go()
        headers = {
            'Authentication': 'Bearer %s' % self.token,
            'Authorization': 'Bearer %s' % self.csrf,
            'X-ARKEA-EFS': self.arkea,
            'X-Csrf-Token': self.csrf,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-REFERER-TOKEN': 'RWDPRO',
        }

        return self.profile.go(website=self.website, data='{}', headers=headers).get_profile()

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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


import ssl
from datetime import timedelta, date
from lxml.etree import XMLSyntaxError
from itertools import groupby

from weboob.tools.date import LinearDateGuesser
from weboob.capabilities.bank import Account, AccountNotFound
from weboob.tools.capabilities.bank.transactions import FrenchTransaction
from weboob.tools.compat import parse_qsl, urlparse
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import HTTPNotFound

from .pages.account_pages import (
    AccountsPage, CBOperationPage, CPTOperationPage, LoginPage, AppGonePage, RibPage,
     UnavailablePage, OtherPage, FrameContainer
)
from .pages.life_insurances import (
    LifeInsurancesPage, LifeInsurancePortal, LifeInsuranceMain, LifeInsuranceUseless,
)
from .pages.investments import (
    LogonInvestmentPage, ProductViewHelper, RetrieveAccountsPage, RetrieveInvestmentsPage, RetrieveLiquidityPage
)
from .pages.landing_pages import JSMiddleFramePage, JSMiddleAuthPage, InvestmentFormPage


__all__ = ['HSBC']


class HSBC(LoginBrowser):
    BASEURL = 'https://client.hsbc.fr'

    app_gone = False

    connection =      URL(r'https://www.hsbc.fr/1/2/hsbc-france/particuliers/connexion', LoginPage)
    login =           URL(r'https://www.hsbc.fr/1/*', LoginPage)
    cptPage =         URL(r'/cgi-bin/emcgi.*\&Cpt=.*',
                          r'/cgi-bin/emcgi.*\&Epa=.*',
                          r'/cgi-bin/emcgi.*\&CPT_IdPrestation.*',
                          r'/cgi-bin/emcgi.*\&Ass_IdPrestation.*',
                          # FIXME are the previous patterns relevant in POST nav?
                          r'/cgi-bin/emcgi',
                          CPTOperationPage)
    cbPage =          URL(r'/cgi-bin/emcgi.*[\&\?]Cb=.*',
                          r'/cgi-bin/emcgi.*\&CB_IdPrestation.*',
                          # FIXME are the previous patterns relevant in POST nav?
                          r'/cgi-bin/emcgi',
                          CBOperationPage)
    appGone =     URL(r'/.*_absente.html',
                      r'/pm_absent_inter.html',
                      '/appli_absente_MBEL.html',
                        AppGonePage)
    rib =             URL(r'/cgi-bin/emcgi', RibPage)
    accounts =        URL(r'/cgi-bin/emcgi', AccountsPage)
    life_insurance_useless = URL(r'/cgi-bin/emcgi', LifeInsuranceUseless)
    unavailable = URL(r'/cgi-bin/emcgi', UnavailablePage)
    frame_page = URL(r'/cgi-bin/emcgi', FrameContainer)

    # other site
    life_insurance_portal = URL(r'/cgi-bin/emcgi', LifeInsurancePortal)
    life_insurance_main = URL('https://assurances.hsbc.fr/fr/accueil/b2c/accueil.html\?pointEntree=PARTIEGENERIQUEB2C', LifeInsuranceMain)
    life_insurances = URL('https://assurances.hsbc.fr/navigation', LifeInsurancesPage)

    # investment pages
    middle_frame_page = URL(r'/cgi-bin/emcgi', JSMiddleFramePage)
    middle_auth_page = URL(r'/cgi-bin/emcgi', JSMiddleAuthPage)
    investment_form_page = URL(
        r'https://www.hsbc.fr/1/[0-9]/authentication/sso-cwd\?customerFullName=.*',
        InvestmentFormPage
    )
    logon_investment_page = URL(r'https://investissements.clients.hsbc.fr/group-wd-gateway-war/gateway/LogonAuthentication', LogonInvestmentPage)
    retrieve_accounts_view = URL(
        r'https://investissements.clients.hsbc.fr/group-wd-gateway-war/gateway/wd/RetrieveProductView',
        RetrieveAccountsPage
    )
    retrieve_investments_page = URL(
        r'https://investissements.clients.hsbc.fr/group-wd-gateway-war/gateway/wd/RetrieveProductView',
        RetrieveInvestmentsPage
    )
    retrieve_liquidity_page = URL(
        r'https://investissements.clients.hsbc.fr/group-wd-gateway-war/gateway/wd/RetrieveProductView',
        RetrieveLiquidityPage
    )


    # catch-all
    other_page = URL(r'/cgi-bin/emcgi', OtherPage)

    def __init__(self, username, password, secret, *args, **kwargs):
        super(HSBC, self).__init__(username, password, *args, **kwargs)
        self.accounts_list = dict()
        self.secret = secret
        self.PEA_LISTING = {}

    def load_state(self, state):
        return

    def prepare_request(self, req):
        preq = super(HSBC, self).prepare_request(req)

        conn = self.session.adapters['https://'].get_connection(preq.url)
        conn.ssl_version = ssl.PROTOCOL_TLSv1

        return preq

    def do_login(self):
        self.session.cookies.clear()

        self.app_gone = False
        self.connection.go()
        self.page.login(self.username)

        no_secure_key_link = self.page.get_no_secure_key()

        if not no_secure_key_link:
            raise BrowserIncorrectPassword()
        self.location(no_secure_key_link)

        self.page.login_w_secure(self.password, self.secret)
        for _ in range(3):
            if self.login.is_here():
                self.page.useless_form()

        self.js_url = self.page.get_js_url()
        home_url = self.page.get_frame()

        if not home_url or not self.page.logged:
            raise BrowserIncorrectPassword()

        self.location(home_url)

    @need_login
    def get_accounts_list(self):
        if not self.accounts_list:
            self.update_accounts_list()
        for a in self.accounts_list.values():
            yield a

    def go_post(self, url, data=None):
        # most of HSBC accounts links are actually handled by js code
        # which convert a GET query string to POST data.
        # not doing so often results in logout by the site
        q = dict(parse_qsl(urlparse(url).query))
        if data:
            q.update(data)
        url = url[:url.find('?')]
        self.location(url, data=q)

    @need_login
    def update_accounts_list(self, iban=True):
        if self.accounts.is_here():
            self.go_post(self.js_url)
        else:
            data = {'debr': 'COMPTES_PAN'}
            self.go_post(self.js_url, data=data)

        for a in self.page.iter_accounts():
            try:
                self.accounts_list[a.id].url = a.url
            except KeyError:
                self.accounts_list[a.id] = a

        if iban:
            self.location(self.js_url, params={'debr': 'COMPTES_RIB'})
            self.page.get_rib(self.accounts_list)

    @need_login
    def _quit_li_space(self):
        if self.life_insurances.is_here():
            self.page.disconnect()

            self.session.cookies.pop('ErisaSession', None)
            self.session.cookies.pop('HBFR-INSURANCE-COOKIE-82', None)

        if self.frame_page.is_here():
            home_url = self.page.get_frame()
            self.js_url = self.page.get_js_url()

            self.location(home_url)

        if self.life_insurance_useless.is_here():
            data = {'debr': 'COMPTES_PAN'}
            self.go_post(self.js_url, data=data)

    @need_login
    def _go_to_life_insurance(self, account):
        self._quit_li_space()

        self.go_post(account.url)

        if self.frame_page.is_here() or self.life_insurance_useless.is_here():
            self.logger.warning('cannot go to life insurance %r', account)
            return False

        data = {'url_suivant': 'SITUATIONCONTRATB2C', 'strNumAdh': ''}
        data.update(self.page.get_lf_attributes(account.id))

        self.life_insurances.go(data=data)
        return True

    @need_login
    def get_history(self, account, coming=False, retry_li=True):
        self._quit_li_space()

        self.update_accounts_list(False)
        account = self.accounts_list[account.id]

        if account.url is None:
            return []

        if account.url.startswith('javascript') or '&Crd=' in account.url:
            raise NotImplementedError()

        if account.type == Account.TYPE_LIFE_INSURANCE:
            if coming is True:
                return []

            try:
                if not self._go_to_life_insurance(account):
                    self._quit_li_space()
                    return []
            except (XMLSyntaxError, HTTPNotFound):
                self._quit_li_space()
                return []
            except AccountNotFound:
                self.go_post(self.js_url)

                # often if we visit life insurance subsite multiple times too quickly, the site just returns an error
                # so we just retry (we might relogin...)
                # TODO find out how to avoid the error, or avoid relogin
                if retry_li:
                    self.logger.warning('life insurance seems unavailable for account %s', account.id)
                    return self.get_history(account, coming, False)

                self.logger.error('life insurance seems unavailable for account %s', account.id)
                return []

            self.life_insurances.go(data={'url_suivant': 'HISTORIQUECONTRATB2C', 'strMonnaie': 'EURO'})

            history = [t for t in self.page.iter_history()]

            self._quit_li_space()

            return history

        try:
            self.go_post(self.accounts_list[account.id].url)
        # sometime go to hsbc life insurance space do logout
        except HTTPNotFound:
            self.app_gone = True
            self.do_logout()
            self.do_login()

        # If we relogin on hsbc, all link have change
        if self.app_gone:
            self.app_gone = False
            self.update_accounts_list()
            self.location(self.accounts_list[account.id].url)

        if self.page is None:
            return []

        if self.cbPage.is_here():
            guesser = LinearDateGuesser(date_max_bump=timedelta(45))
            history = list(self.page.get_history(date_guesser=guesser))
            for url, params in self.page.get_params(self.url):
                self.location(url, params=params)
                if self.cbPage.is_here():
                    history.extend(self.page.get_history(date_guesser=guesser))
            history.extend(self.get_monthly_transactions(history))
            return [tr for tr in history if (coming and tr.date > date.today()) or (not coming and tr.date <= date.today())]
        elif not coming:
            return self._get_history()
        else:
            raise NotImplementedError()

    def get_monthly_transactions(self, trs):
        groups = [list(g) for k, g in groupby(sorted(trs, key=lambda tr: tr.date), lambda tr: tr.date)]
        trs = []
        for group in groups:
            if group[0].date > date.today():
                continue
            tr = FrenchTransaction()
            tr.raw = tr.label = u"RELEVE CARTE %s" % group[0].date
            tr.amount = -sum([t.amount for t in group])
            tr.date = tr.rdate = tr.vdate = group[0].date
            tr.type = FrenchTransaction.TYPE_CARD_SUMMARY
            trs.append(tr)
        return trs

    def _get_history(self):
        for tr in self.page.get_history():
            yield tr

    def get_investments(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            return self.get_life_investments(account)
        elif account.type in (Account.TYPE_PEA,):
            return self.get_pea_investments(account)
        else:
            raise NotImplementedError()

    def get_pea_investments(self, account):
        assert account.type in (Account.TYPE_PEA, Account.TYPE_MARKET)
        if not self.PEA_LISTING:
            self._go_to_wealth_accounts()
        return self.PEA_LISTING['investments']

    def get_life_investments(self, account, retry_li=True):

        self._quit_li_space()

        self.update_accounts_list(False)
        account = self.accounts_list[account.id]

        try:
            if not self._go_to_life_insurance(account):
                self._quit_li_space()
                return []
        except (XMLSyntaxError, HTTPNotFound):
            self._quit_li_space()
            return []
        except AccountNotFound:
            self.go_post(self.js_url)

            # often if we visit life insurance subsite multiple times too quickly, the site just returns an error
            # retry (we might relogin...)
            if retry_li:
                self.logger.warning('life insurance seems unavailable for account %s', account.id)
                return self.get_investments(account, False)

            self.logger.error('life insurance seems unavailable for account %s', account.id)
            return []

        investments = [i for i in self.page.iter_investments()]

        self._quit_li_space()

        return investments

    def _go_to_wealth_accounts(self):
        if not hasattr(self.page, 'get_middle_frame_url'):
            # if we can catch the URL, we go directly, else we need to browse
            # the website
            self.update_accounts_list()

        self.location(self.page.get_middle_frame_url())
        self.location(self.page.get_patrimoine_url())
        self.page.go_next()
        self.page.go_to_logon()
        helper = ProductViewHelper(self)
        # we need to go there to initialize the session
        self.PEA_LISTING['accounts'] = list(helper.retrieve_accounts())
        self.PEA_LISTING['liquidities'] = list(helper.retrieve_liquidity_account())
        self.PEA_LISTING['investments'] = list(helper.retrieve_invests())
        self.connection.go()

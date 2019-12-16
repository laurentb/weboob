# -*- coding: utf-8 -*-

# Copyright(C) 2016      James GALT
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

from __future__ import unicode_literals

from weboob.browser import URL, LoginBrowser, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ClientError, ServerError
from weboob.capabilities.base import empty, NotAvailable

from .pages import (
    LoginPage, AccountsPage, AccountHistoryPage, AmundiInvestmentsPage, AllianzInvestmentPage,
    EEInvestmentPage, EEInvestmentPerformancePage, EEInvestmentDetailPage, EEProductInvestmentPage,
    EresInvestmentPage, CprInvestmentPage, BNPInvestmentPage, BNPInvestmentApiPage, AxaInvestmentPage,
    EpsensInvestmentPage, EcofiInvestmentPage, SGGestionInvestmentPage, SGGestionPerformancePage,
)


class AmundiBrowser(LoginBrowser):
    TIMEOUT = 120.0

    login = URL(r'authenticate', LoginPage)
    authorize = URL(r'authorize', LoginPage)
    accounts = URL(r'api/individu/positionFonds\?flagUrlFicheFonds=true&inclurePositionVide=false', AccountsPage)
    account_history = URL(r'api/individu/operations\?valeurExterne=false&filtreStatutModeExclusion=false&statut=CPTA', AccountHistoryPage)

    # Amundi.fr investments
    amundi_investments = URL(r'https://www.amundi.fr/fr_part/product/view', AmundiInvestmentsPage)
    # EEAmundi browser investments
    ee_investments = URL(r'https://www.amundi-ee.com/part/home_fp&partner=PACTEO_SYS', EEInvestmentPage)
    ee_performance_details = URL(r'https://www.amundi-ee.com/psAmundiEEPart/ezjscore/call(.*)_tab_2', EEInvestmentPerformancePage)
    ee_investment_details = URL(r'https://www.amundi-ee.com/psAmundiEEPart/ezjscore/call(.*)_tab_5', EEInvestmentDetailPage)
    # EEAmundi product investments
    ee_product_investments = URL(r'https://www.amundi-ee.com/product', EEProductInvestmentPage)
    # Allianz GI investments
    allianz_investments = URL(r'https://fr.allianzgi.com', AllianzInvestmentPage)
    # Eres investments
    eres_investments = URL(r'https://www.eres-group.com/eres/new_fiche_fonds.php', EresInvestmentPage)
    # CPR asset management investments
    cpr_investments = URL(r'https://www.cpr-am.fr/particuliers/product/view', CprInvestmentPage)
    # BNP Paribas Epargne Retraite Entreprises
    bnp_investments = URL(r'https://www.epargne-retraite-entreprises.bnpparibas.com/entreprises/fonds', BNPInvestmentPage)
    bnp_investment_api = URL(r'https://www.epargne-retraite-entreprises.bnpparibas.com/api2/funds/overview/(?P<fund_id>.*)', BNPInvestmentApiPage)
    # AXA investments
    axa_investments = URL(r'https://(.*).axa-im.fr/fr/fund-page', AxaInvestmentPage)
    # Epsens investments
    epsens_investments = URL(r'https://www.epsens.com/information-financiere', EpsensInvestmentPage)
    # Ecofi investments
    ecofi_investments = URL(r'http://www.ecofi.fr/fr/fonds/dynamis-solidaire', EcofiInvestmentPage)
    # Société Générale gestion investments
    sg_gestion_investments = URL(r'https://www.societegeneralegestion.fr/psSGGestionEntr/productsheet/view/idvm', SGGestionInvestmentPage)
    sg_gestion_performance = URL(r'https://www.societegeneralegestion.fr/psSGGestionEntr/ezjscore/call', SGGestionPerformancePage)

    def do_login(self):
        data = {
            'username': self.username,
            'password': self.password,
        }
        try:
            self.login.go(json=data)
            self.token = self.authorize.go().get_token()
        except ClientError:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_accounts(self):
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.accounts.go(headers=headers)
        company_name = self.page.get_company_name()
        if empty(company_name):
            self.logger.warning('Could not find the company name for these accounts.')
        for account in self.page.iter_accounts():
            account.company_name = company_name
            yield account

    @need_login
    def iter_investment(self, account):
        if account.balance == 0:
            self.logger.info('Account %s has a null balance, no investment available.', account.label)
            return
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.accounts.go(headers=headers)

        ignored_urls = (
            'www.sggestion-ede.com/product',  # Going there leads to a 404
            'www.assetmanagement.hsbc.com',  # Information not accessible
            'www.labanquepostale-am.fr/nos-fonds',  # Nothing interesting there
        )

        handled_urls = (
            'www.amundi.fr/fr_part',  # AmundiInvestmentsPage
            'www.amundi-ee.com/part/home_fp',  # EEInvestmentDetailPage & EEInvestmentPerformancePage
            'www.amundi-ee.com/product',  # EEProductInvestmentPage
            'fr.allianzgi.com/fr-fr',  # AllianzInvestmentPage
            'www.eres-group.com/eres',  # EresInvestmentPage
            'www.cpr-am.fr/particuliers/product',  # CprInvestmentPage
            'www.epargne-retraite-entreprises.bnpparibas.com',  # BNPInvestmentPage
            'axa-im.fr/fr/fund-page',  # AxaInvestmentPage
            'www.epsens.com/information-financiere',  # EpsensInvestmentPage
            'www.ecofi.fr/fr/fonds/dynamis-solidaire',  # EcofiInvestmentPage
            'www.societegeneralegestion.fr',  # SGGestionInvestmentPage
        )

        for inv in self.page.iter_investments(account_id=account.id):
            if inv._details_url:
                # Only go to known details pages to avoid logout on unhandled pages
                if any(url in inv._details_url for url in handled_urls):
                    self.fill_investment_details(inv)
                else:
                    if not any(url in inv._details_url for url in ignored_urls):
                        # Not need to raise warning if the URL is already known and ignored
                        self.logger.warning('Investment details on URL %s are not handled yet.', inv._details_url)
                    inv.asset_category = NotAvailable
                    inv.recommended_period = NotAvailable
            yield inv

    @need_login
    def fill_investment_details(self, inv):
        # Going to investment details may lead to various websites.
        # This method handles all the already encountered pages.
        try:
            self.location(inv._details_url)
        except ServerError:
            # Some URLs return a 500 even on the website
            inv.asset_category = NotAvailable
            inv.recommended_period = NotAvailable
            return inv

        # Pages with only asset category available
        if (self.amundi_investments.is_here() or
            self.allianz_investments.is_here() or
            self.axa_investments.is_here()):
            inv.asset_category = self.page.get_asset_category()
            inv.recommended_period = NotAvailable

        # Pages with asset category & recommended period
        elif (self.eres_investments.is_here() or
            self.cpr_investments.is_here() or
            self.ee_product_investments.is_here() or
            self.epsens_investments.is_here() or
            self.ecofi_investments.is_here()):
            self.page.fill_investment(obj=inv)

        # Particular cases
        elif self.ee_investments.is_here():
            inv.recommended_period = self.page.get_recommended_period()
            details_url = self.page.get_details_url()
            performance_url = self.page.get_performance_url()
            if details_url:
                self.location(details_url)
                if self.ee_investment_details.is_here():
                    inv.asset_category = self.page.get_asset_category()
            if performance_url:
                self.location(performance_url)
                if self.ee_performance_details.is_here():
                    # The investments JSON only contains 1 & 5 years performances
                    # If we can access EEInvestmentPerformancePage, we can fetch all three
                    # values (1, 3 and 5 years), in addition the values are more accurate here.
                    complete_performance_history = self.page.get_performance_history()
                    if complete_performance_history:
                        inv.performance_history = complete_performance_history

        elif self.sg_gestion_investments.is_here():
            # Fetch asset category & recommended period
            self.page.fill_investment(obj=inv)
            # Fetch all performances on the details page
            performance_url = self.page.get_performance_url()
            if performance_url:
                self.location(performance_url)
                inv.performance_history = self.page.get_performance_history()

        elif self.bnp_investments.is_here():
            # We fetch the fund ID and get the attributes directly from the BNP-ERE API
            fund_id = self.page.get_fund_id()
            if fund_id:
                # Specify the 'Accept' header otherwise the server returns WSDL instead of JSON
                self.bnp_investment_api.go(fund_id=fund_id, headers={'Accept': 'application/json'})
                self.page.fill_investment(obj=inv)
            else:
                self.logger.warning('Could not fetch the fund_id for BNP investment %s.', inv.label)
                inv.asset_category = NotAvailable
                inv.recommended_period = NotAvailable

        return inv

    @need_login
    def iter_history(self, account):
        headers = {'X-noee-authorization': 'noeprd %s' % self.token}
        self.account_history.go(headers=headers)
        for tr in self.page.iter_history(account=account):
            yield tr


class EEAmundi(AmundiBrowser):
    # Careful if you modify the BASEURL, also verify Amundi's Abstract modules
    BASEURL = 'https://www.amundi-ee.com/psf/'


class TCAmundi(AmundiBrowser):
    # Careful if you modify the BASEURL, also verify Amundi's Abstract modules
    BASEURL = 'https://epargnants.amundi-tc.com/psf/'

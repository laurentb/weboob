# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
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

import re
from datetime import timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError, BrowserHTTPNotFound
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.compat import urlparse
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.tools.date import LinearDateGuesser

from weboob.capabilities.base import empty, find_object
from weboob.capabilities.bank import Account, AccountNotFound

from .pages import (
    HomePage, LoginPage, LoggedOutPage, PerimeterDetailsPage, PerimeterPage, RibPage, AccountsPage,
    WealthPage, LoansPage, CardsPage, MultipleCardsPage, HistoryPage, OtherHistoryPage,
    SavingsHistoryPage, OtherSavingsHistoryPage, FailedHistoryPage, PredicaRedirectionPage,
    PredicaInvestmentsPage, NetfincaRedirectionPage, NetfincaLanding, NetfincaDetailsPage, NetfincaReturnPage,
    NetfincaToCragr, BGPIRedirectionPage, BGPISpace, BGPIInvestmentPage, ProfilePage,
)

from .netfinca_browser import NetfincaBrowser


__all__ = ['CragrRegion']


class CragrRegion(LoginBrowser):
    # Login
    home = URL(r'/$', r'/particuliers.html', HomePage)
    login = URL(r'/stb/entreeBam$', LoginPage)
    logged_out = URL(r'.*', LoggedOutPage)

    # Perimeters
    perimeter_details_page = URL(r'/stb/.*act=Perimetre&stbpg=pagePU', PerimeterDetailsPage)
    perimeter_page = URL(r'/stb/.*act=ChgPerim.*stbpg=pagePU', PerimeterPage)

    # Credit cards
    cards_page = URL(r'/stb/.*fwkaid=.*fwkpid=.*', r'/stb.*(fwkaction|sessionAPP)=Cartes.*', CardsPage)
    multiple_cards_page = URL(r'/stb/.*fwkaid=.*fwkpid=.*', r'/stb.*(fwkaction|sessionAPP)=Cartes.*', MultipleCardsPage)

    # History & account details
    rib_page = URL(r'.*action=Rib.*', RibPage)
    history = URL(r'/stb/.*fwkaid=.*fwkpid=.*', HistoryPage)
    other_history = URL(r'/stb/.*fwkaid=.*fwkpid=.*', OtherHistoryPage)
    savings_history = URL(r'/stb/.*fwkaid=.*fwkpid=.*', SavingsHistoryPage)
    other_savings_history = URL(r'/stb/.*fwkaid=.*fwkpid=.*', OtherSavingsHistoryPage)
    failed_history = URL(r'/stb/.*fwkaid=.*fwkpid=.*', FailedHistoryPage)

    # Various investment spaces (Predica, Netfinca, BGPI)
    predica_redirection = URL(
        r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&site=(?P<website>[^&]+)&typeaction=reroutage_aller&sdt=(?P<sdt>[^&]+)&parampartenaire=(?P<partenaire>[^&]+)',
        PredicaRedirectionPage
    )
    predica_investments = URL(r'https://npcprediweb.predica.credit-agricole.fr/rest/detailEpargne/contrat/', PredicaInvestmentsPage)

    netfinca_redirection = URL(
        r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&site=CATITRES&typeaction=reroutage_aller',
        NetfincaRedirectionPage
    )
    netfinca_details = URL(
        r'https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.WalletVal\?nump=(?P<account_id>[^&]+):(?P<code>[^&]+)',
        NetfincaDetailsPage
    )
    netfinca_return = URL(
        r'https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect',
        NetfincaReturnPage
    )
    netfinca_landing = URL(
        r'https://www.cabourse.credit-agricole.fr/netfinca-titres/servlet/com.netfinca.frontcr.navigation.AccueilBridge.*',
        NetfincaLanding
    )
    netfinca_to_cragr = URL(r'/stb/entreeBam\?identifiantBAM=.*', NetfincaToCragr)

    bgpi_redirection = URL(
        r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&site=BGPI&typeaction=reroutage_aller&sdt=BGPI&parampartenaire=',
        BGPIRedirectionPage
    )
    bgpi_space = URL(r'https://bgpi-gestionprivee.credit-agricole.fr/bgpi/Logon.do.*', BGPISpace)
    bgpi_investments = URL(r'https://bgpi-gestionprivee.credit-agricole.fr/bgpi/CompteDetail.do.*', BGPIInvestmentPage)

    # Accounts
    accounts = URL(r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&act=Synthcomptes.*',
                   r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&act=Releves.*',
                   r'/stb/(collecteNI|entreeBam)\?fwkaid=.*&fwkpid=.*Synthcomptes.*',
                   r'/stb/.*fwkaid=.*fwkpid=.*', AccountsPage)

    wealth = URL(r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&act=Synthepargnes',
                 r'/stb/(collecteNI|entreeBam)\?fwkaid=.*&fwkpid=.*Synthepargnes.*', WealthPage)

    loans = URL(r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&act=Synthcredits',
                r'/stb/(collecteNI|entreeBam)\?fwkaid=.*&fwkpid=.*Synthcredits.*', LoansPage)

    # Profile
    profile = URL(r'/stb/entreeBam\?sessionSAG=(?P<session_value>[^&]+)&stbpg=pagePU&act=Coordonnees', ProfilePage)


    def __init__(self, website, *args, **kwargs):
        super(CragrRegion, self).__init__(*args, **kwargs)
        self.BASEURL = 'https://%s' % website
        self.ORIGIN_URL = self.BASEURL
        self.website = website
        self.session_value = None
        self.cragr_code = None
        self.perimeters = []

        # Netfinca browser:
        self.weboob = kwargs.pop('weboob')
        dirname = self.responses_dirname
        if dirname:
            dirname += '/netfinca'
        self.netfinca = NetfincaBrowser(
            '',
            '',
            logger=self.logger,
            weboob=self.weboob,
            responses_dirname=dirname,
            proxy=self.PROXIES
        )

    def deinit(self):
        super(CragrRegion, self).deinit()
        self.netfinca.deinit()

    def do_login(self):
        # Re-set the BASEURL to the origin URL in case of logout
        self.BASEURL = self.ORIGIN_URL

        # From the home page, fetch the login url to go to login page
        login_url = self.home.go().get_login_url()
        if not login_url:
            raise BrowserUnavailable("L'adresse URL %s n'est pas gérée actuellement." % self.ORIGIN_URL)

        parsed_url = urlparse(login_url)
        self.BASEURL = '%s://%s' % (parsed_url.scheme, parsed_url.netloc)

        # Go to login page and POST the username
        login_data = {
            'CCPTE': self.username,
            'urlOrigine': self.ORIGIN_URL,
            'typeAuthentification': 'CLIC_ALLER',
            'situationTravail': 'BANCAIRE',
            'origine': 'vitrine',
            'matrice': 'true',
            'canal': 'WEB',
        }
        self.login.go(data=login_data)
        assert self.login.is_here()

        # POST the password and fetch the URL after login
        self.page.submit_password(self.username, self.password)
        url_after_login = self.page.get_accounts_url()

        # In case of wrongpass, instead of a URL, the node will contain a message such as
        # 'Votre identification est incorrecte, veuillez ressaisir votre numéro de compte et votre code d'accès'
        if not url_after_login.startswith('https'):
            raise BrowserIncorrectPassword(url_after_login)

        # The session value is necessary for correct navigation.
        self.location(url_after_login)

        self.accounts.go(session_value=self.session_value)
        assert self.accounts.is_here()

        # No need to get perimeters in case of re-login
        if not self.perimeters:
            self.get_all_perimeters()

    def access_perimeter_details(self):
        params = {
            'sessionSAG': self.session_value,
            'stbpg': 'pagePU',
            'act': 'Perimetre'
        }
        self.login.go(params=params)

    def switch_perimeter(self):
        params = {
            'sessionSAG': self.session_value,
            'stbpg': 'pagePU',
            'act': 'ChgPerim',
            'typeaction': 'ChgPerim',
            'stbzn' :'global'
        }
        self.login.go(params=params)

    def get_all_perimeters(self):
        # Multi-perimeters connections have an 'Espace Autres Comptes' button
        if self.page.no_other_perimeter():
            self.logger.warning('This connection has only 1 perimeter.')
            self.perimeters = ['main']
            return
        # If the button exists, go to the perimeters details:
        self.access_perimeter_details()
        if self.page.has_two_perimeters():
            self.logger.warning('This connection has 2 perimeters.')
            self.perimeters.append(self.page.get_perimeter_name())
            self.accounts.stay_or_go(session_value=self.session_value)
            self.access_perimeter_details()
            self.switch_perimeter()
            self.perimeters.append(self.page.get_perimeter_name())
        else:
            self.logger.warning('This connection has multiple perimeters.')
            self.perimeters.append(self.page.get_perimeter_name())
            for perimeter in self.page.get_multiple_perimeters():
                self.accounts.stay_or_go(session_value=self.session_value)
                self.access_perimeter_details()
                perimeter_url = self.page.get_perimeter_url(perimeter)
                if perimeter_url:
                    self.location(perimeter_url)
                    self.switch_perimeter()
                    self.perimeters.append(self.page.get_perimeter_name())
                else:
                    self.logger.warning('Perimeter %s has no URL, this perimeter will be skipped.', perimeter)

    @need_login
    def iter_accounts(self):
        '''
        Each perimeter has 3 accounts pages: Regular, Wealth/Savings and Loans.
        We must handle two different perimeter cases:
        - Unique perimeter: we already are on the accounts page, simply
        return the unique perimeter accounts.
        - Multiple perimeters: visit all perimeters one by one and return all accounts.
        '''
        accounts_list = []
        if len(self.perimeters) == 1:
            self.accounts.stay_or_go(session_value=self.session_value)
            for account in self.iter_perimeter_accounts(iban=True, all_accounts=True):
                account._perimeter = 'main'
                accounts_list.append(account)
        else:
            for perimeter in self.perimeters:
                self.go_to_perimeter(perimeter)
                for account in self.iter_perimeter_accounts(iban=True, all_accounts=True):
                    account._perimeter = perimeter
                    accounts_list.append(account)

        # Do not return accounts with empty balances or invalid IDs
        valid_accounts = []
        for account in accounts_list:
            if empty(account.balance):
                self.logger.warning('Account %s %s will be skipped because it has no balance.', account.label, account.id)
            else:
                valid_accounts.append(account)

        return valid_accounts

    @need_login
    def iter_perimeter_accounts(self, iban, all_accounts):
        '''
        In order to use this method, we must pass the 3 accounts URLs: Regular, Wealth and Loans.
        Accounts may appear on several URLs: we must check for duplicates before adding to cragr_accounts.
        Once we fetched all cragr accounts, we go to the Netfinca space to get Netfinca accounts.
        If there are account duplicates, we preferably yield the Netfinca version because it is more
        complete ; in addition, Netfinca may contain accounts that do not appear on the cragr website.
        '''
        cragr_accounts = []

        # Regular accounts (Checking and Savings)
        self.accounts.stay_or_go(session_value=self.session_value)
        self.page.set_cragr_code()
        for account in self.page.iter_accounts():
            if iban and account._form:
                account.iban = self.get_account_iban(account._form)
            if account.id not in [a.id for a in cragr_accounts]:
                cragr_accounts.append(account)

        # Wealth accounts (PEA, Market, Life Insurances, PERP...)
        self.wealth.go(session_value=self.session_value)
        wealth_accounts = []
        assert self.wealth.is_here()

        # We first store the wealth accounts in a list because we
        # must avoid requests to BGPI during account pagination
        for account in self.page.iter_wealth_accounts():
            if account.id not in [a.id for a in cragr_accounts] and account.id != '0':
                wealth_accounts.append(account)

        for account in wealth_accounts:
            if all_accounts and account.url == 'BGPI':
                # Accounts from the BGPI space require going
                # to the BGPI space to get account details
                self.bgpi_redirection.go(session_value=self.session_value)
                bgpi_url = self.page.get_bgpi_url()
                if bgpi_url:
                    self.location(bgpi_url)
                    account.balance, account.currency, account.label, account.url = self.page.get_account_details(account.id)
                    if account.type == Account.TYPE_UNKNOWN:
                        BGPI_TYPES = {
                            'VENDOME OPTIMUM EURO': Account.TYPE_LIFE_INSURANCE,
                        }
                        account.type = BGPI_TYPES.get(account.label, Account.TYPE_UNKNOWN)

                    if account.type == Account.TYPE_UNKNOWN:
                        # BGPI accounts must be typed in order to fetch their investments
                        self.logger.warning(
                            'Account %s is untyped: please add "%s" to the BGPI_TYPES dictionary.',
                            account.id,
                            account.label
                        )
                # Go back to the main Cragr website afterwards
                self.wealth.go(session_value=self.session_value)

            # Sometimes the balance is not displayed here, so when possible,
            # we go to the account details to fetch it
            if all_accounts and empty(account.balance) and account.url and 'fwkaid' in account.url:
                    self.location(account.url)
                    account.balance = self.page.get_account_balance()

            cragr_accounts.append(account)

        # Loans & revolving credits
        self.loans.go(session_value=self.session_value)
        assert self.loans.is_here()
        for loan in self.page.iter_loans():
            if loan.id not in [a.id for a in cragr_accounts]:
                cragr_accounts.append(loan)

        # Deferred cards
        self.accounts.stay_or_go(session_value=self.session_value)
        for card in self.iter_deferred_cards(cragr_accounts):
            if card.id not in [a.id for a in cragr_accounts]:
                cragr_accounts.append(card)

        # This method is also used to update the account forms
        # but there is no need to go to Netfinca in this case
        if all_accounts:
            perimeter_accounts = []
            for netfinca_account in self.get_netfinca_accounts():
                netfinca_account.number = netfinca_account.id
                netfinca_account.url = 'CATITRES'
                netfinca_account._form = None

                # For PEA accounts, we must go to the PEA detail and fetch the balance
                # without liquidities because they are already on the DAV PEA:
                if netfinca_account.type == Account.TYPE_PEA and netfinca_account.label != 'DAV PEA':
                    self.netfinca_details.go(account_id=netfinca_account.id, code=self.cragr_code)
                    netfinca_account.balance = self.page.get_balance()

                perimeter_accounts.append(netfinca_account)

            for cragr_account in cragr_accounts:
                if cragr_account.id not in [a.id for a in perimeter_accounts]:
                    perimeter_accounts.append(cragr_account)
        else:
            perimeter_accounts = cragr_accounts

        return perimeter_accounts

    @need_login
    def get_account_iban(self, form):
        form.submit()
        rib_url = self.page.get_rib_url()
        if rib_url:
            self.location(rib_url)
            assert self.rib_page.is_here(), 'RIB URL led to an unhandled page.'
            return self.page.get_iban()

    @need_login
    def get_netfinca_accounts(self):
        try:
            self.netfinca_redirection.go(session_value=self.session_value)
        except BrowserHTTPNotFound:
            pass
        else:
            if self.page.no_netfinca_access():
                # This perimeter has no available Netfinca space
                return
            url = self.page.get_url()
            if 'netfinca' in url:
                self.location(url)
                self.netfinca.session.cookies.update(self.session.cookies)
                self.netfinca.accounts.go()
                for account in self.netfinca.iter_accounts():
                    yield account
            self.return_from_netfinca()

    @need_login
    def return_from_netfinca(self):
        # If we do not POST the return form correctly, we will be logged out.
        self.netfinca_return.go().return_from_netfinca()

    @need_login
    def iter_deferred_cards(self, perimeter_accounts):
        cards_list = []
        for card_link, parent_account in self.page.get_cards_parameters():
            self.page.go_to_card(card_link)
            if self.accounts.is_here():
                self.logger.warning('Could not access card details for parent account %s, it will be skipped.', parent_account)
                continue
            if self.multiple_cards_page.is_here():
                # There are multiple credit cards on this account
                card_parent = find_object(perimeter_accounts, id=parent_account)
                for card in self.page.iter_multiple_cards():
                    card.parent = card_parent
                    card._card_link = card_link
                    cards_list.append(card)
            elif self.cards_page.is_here():
                # There is only one credit card for this account
                card = self.page.get_unique_card()
                card.parent = find_object(perimeter_accounts, id=parent_account)
                card._card_link = card_link
                cards_list.append(card)

        return cards_list

    def go_to_perimeter(self, perimeter):
        '''
        This method enables correct navigation between the perimeters.
        The behavior is really sensitive: for example, if you call
        switch_perimeter() whereas you are already on the correct perimeter,
        all the account forms will systematically fail.
        '''
        if len(self.perimeters) == 1:
            # There is only one perimeter, no need to switch.
            return
        elif len(self.perimeters) == 2:
            self.accounts.stay_or_go(session_value=self.session_value)
            if perimeter == self.page.get_perimeter_name():
                # We are already on the correct perimeter.
                return
            else:
                # Going to the other perimeter.
                self.access_perimeter_details()
                self.switch_perimeter()
        else:
            # This connection has multiple perimeters.
            self.accounts.stay_or_go(session_value=self.session_value)
            if perimeter == self.page.get_perimeter_name():
                # We are already on the correct perimeter.
                return
            self.access_perimeter_details()
            perimeter_name = perimeter.split(':')[1].strip()
            perimeter_url = self.page.get_perimeter_url(perimeter_name)
            if perimeter_url:
                self.location(perimeter_url)
                self.switch_perimeter()
            else:
                self.logger.warning('No available link for perimeter %s: this perimeter will be skipped.', perimeter)

    @need_login
    def iter_history(self, account, coming=False):
        handled_history_types = (
            Account.TYPE_CHECKING,
            Account.TYPE_CARD,
            Account.TYPE_SAVINGS,
            Account.TYPE_LOAN,
            Account.TYPE_PEA,
        )
        if account.type not in handled_history_types:
            self.unhandled_method(account.id)
            return

        if account.type == Account.TYPE_CARD:
            self.go_to_perimeter(account._perimeter)
            self.accounts.stay_or_go(session_value=self.session_value)
            self.page.go_to_card(account._card_link)

            assert (self.cards_page.is_here() or self.multiple_cards_page.is_here()), \
                   'Failed to reach card details for card %s.' % account.id

            if self.multiple_cards_page.is_here():
                # We need to go to the correct card transactions with its number.
                card_url = self.page.get_transactions_link(account._raw_number)
                self.location(card_url)

            # When there are several future coming summaries,
            # we must skip the ongoing one but fetch the other ones
            # even if they are in the future.
            ongoing_coming = self.page.get_ongoing_coming()

            card_transactions = []
            latest_date = None
            for tr in self.page.get_card_transactions(latest_date, ongoing_coming):
                card_transactions.append(tr)

            if not card_transactions:
                return

            # Pagination: we must fetch the date of the last transaction
            # because the summary of next transactions may not
            # be available on the next page
            latest_date = card_transactions[-1].date
            next_page_url = self.page.get_next_page()
            while next_page_url:
                self.location(next_page_url)
                for tr in self.page.get_card_transactions(latest_date, ongoing_coming):
                    card_transactions.append(tr)
                next_page_url = self.page.get_next_page()

            for tr in sorted_transactions(card_transactions):
                yield tr
            return

        # Transactions of accounts without form/url or with 'CATITRES' and 'bgpi' in url cannot be handled.
        if not account._form and (not account.url or 'CATITRES' in account.url or 'bgpi' in account.url):
            self.unhandled_method(account.id)
            return

        # Access acount details:
        if account.url:
            # Refresh the session_value before going to the account URL
            new_session_value = 'sessionSAG=' + self.session_value
            updated_url = re.sub(r'sessionSAG=([^&]+)', new_session_value, account.url)
            self.location(updated_url)

        elif account._form:
            # We cannot use forms if we are not on the account's perimeter:
            # we need to go to the correct perimeter and refresh forms.
            # The form submission sometimes fails so we try several
            # times until we get to the account history page.
            for form in range(3):
                self.accounts.stay_or_go(session_value=self.session_value)
                self.go_to_perimeter(account._perimeter)

                # No need to fetch IBANs and Netfinca accounts just to fetch an account form
                refreshed_account = find_object(self.iter_perimeter_accounts(iban=False, all_accounts=False), AccountNotFound, id=account.id)
                refreshed_account._form.submit()
                if self.failed_history.is_here():
                    self.logger.warning('Form submission failed to reach the account history, we try again.')
                    continue
                break

        # 4 types of history pages were identified so far
        if not (self.history.is_here()
                or self.other_history.is_here()
                or self.savings_history.is_here()
                or self.other_savings_history.is_here()):
            self.unhandled_method(account.id)

        date_guesser = LinearDateGuesser(date_max_bump=timedelta(30))
        for tr in self.page.iter_history(date_guesser=date_guesser):
            yield tr

    @need_login
    def iter_investment(self, account):
        if account.balance == 0:
            return

        handled_invest_accounts = (
            Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE,
            Account.TYPE_CAPITALISATION, Account.TYPE_PERP, Account.TYPE_PERCO,
        )
        if account.type not in handled_invest_accounts:
            self.unhandled_method(account.id)
            return

        if account.label == 'DAV PEA':
            # 'PEA Espèces'
            yield create_french_liquidity(account.balance)
            return

        if account.url:
            if 'PREDICA' in account.url:
                # Fetch investments on Predica space
                for inv in self.get_predica_investments(account):
                    yield inv

            elif 'CATITRES' in account.url:
                # Fetch investments on Netfinca space
                for inv in self.get_netfinca_investments(account):
                    yield inv

            elif 'bgpi' in account.url:
                # Fetch investments on BGPI space
                self.location(account.url)
                if self.bgpi_investments.is_here():
                    for inv in self.page.iter_investments():
                        yield inv

            # Go back to the main Cragr website afterwards
            self.accounts.stay_or_go(session_value=self.session_value)

    def get_predica_investments(self, account):
        # We need to extract the account values from a string that has the format
        # "javascript:lancerPuPartenaireParam('PREDICA2','CONTRAT','96732184641');"
        m = re.search(r'\((.*)\)', account.url)
        if m:
            self.go_to_perimeter(account._perimeter)
            values = m.group(1).replace("'", "").split(',')
            try:
                self.predica_redirection.go(session_value=self.session_value, website=values[0], sdt=values[1], partenaire=values[2])
            except ServerError:
                self.logger.warning('Server returned error when fetching investments for account id %s', account.id)
            else:
                self.predica_investments.go()
                return self.page.iter_investments()
        self.logger.warning('Could not reach the investments for account %s', account.id)
        return []

    def get_netfinca_investments(self, account):
        self.go_to_perimeter(account._perimeter)
        try:
            self.netfinca_redirection.go(session_value=self.session_value)
        except BrowserHTTPNotFound:
            pass
        else:
            url = self.page.get_url()
            if 'netfinca' in url:
                self.location(url)
                self.netfinca.session.cookies.update(self.session.cookies)
                self.netfinca.accounts.go()
                investments = []
                for inv in self.netfinca.iter_investments(account):
                    if inv.code == 'XX-liquidity' and account.type == Account.TYPE_PEA:
                        # Liquidities are already fetched on the "PEA espèces"
                        continue
                    investments.append(inv)
                self.return_from_netfinca()
                return investments

        self.logger.warning('Could not reach the investments for account %s', account.id)
        return []

    def unhandled_method(self, account_id):
        # This method avoids code duplication for all accounts
        # that have no available history or investments.
        self.logger.warning('This method is not handled for account %s.', account_id)
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        self.profile.go(session_value=self.session_value)
        if self.profile.is_here():
            return self.page.get_profile()

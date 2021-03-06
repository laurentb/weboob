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

# yapf-compatible

from __future__ import unicode_literals

from decimal import Decimal
import re

from weboob.capabilities.bank import Account, Loan, Per, PerProviderType, Transaction, AccountNotFound, RecipientNotFound
from weboob.capabilities.base import empty, NotAvailable, strict_find_object
from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError, ClientError, BrowserHTTPNotFound, HTTPNotFound
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword, ActionNeeded
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.decorators import retry

from .pages import (
    LoginPage, LoggedOutPage, KeypadPage, SecurityPage, ContractsPage, FirstConnectionPage, AccountsPage, AccountDetailsPage,
    TokenPage, ChangePasswordPage, IbanPage, HistoryPage, CardsPage, CardHistoryPage, NetfincaRedirectionPage, PredicaRedirectionPage,
    PredicaInvestmentsPage, ProfilePage, ProfileDetailsPage, ProProfileDetailsPage, LifeInsuranceInvestmentsPage,
)
from .transfer_pages import (
    RecipientsPage, TransferPage, TransferTokenPage,
)

from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .netfinca_browser import NetfincaBrowser

__all__ = ['CreditAgricoleBrowser']


class CreditAgricoleBrowser(LoginBrowser):
    login_page = URL(r'particulier/acceder-a-mes-comptes.html$', LoginPage)
    keypad = URL(r'particulier/acceder-a-mes-comptes.authenticationKeypad.json', KeypadPage)
    security_check = URL(r'particulier/acceder-a-mes-comptes.html/j_security_check', SecurityPage)
    first_connection = URL(r'.*/operations/interstitielles/premiere-connexion.html', FirstConnectionPage)
    logged_out = URL(r'.*', LoggedOutPage)
    token_page = URL(r'libs/granite/csrf/token.json', TokenPage)
    change_password = URL(r'(?P<space>[\w-]+)/operations/interstitielles/code-personnel.html', ChangePasswordPage)

    contracts_page = URL(
        r'(?P<space>[\w-]+)/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)', ContractsPage
    )

    accounts_page = URL(r'[\w-]+/operations/synthese.html', AccountsPage)

    account_details = URL(
        r'(?P<space>[\w-]+)/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
        AccountDetailsPage
    )

    account_iban = URL(
        r'(?P<space>[\w-]+)/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json', IbanPage
    )

    cards = URL(r'(?P<space>[\w-]+)/operations/(?P<op>.*)/mes-cartes/jcr:content.listeCartesParCompte.json', CardsPage)

    history = URL(r'(?P<space>[\w-]+)/operations/synthese/detail-comptes/jcr:content.n3.operations.json', HistoryPage)

    card_history = URL(
        r'(?P<space>[\w-]+)/operations/synthese/detail-comptes/jcr:content.n3.operations.encours.carte.debit.differe.json',
        CardHistoryPage
    )

    life_insurance_investments = URL(
        r'(?P<space>[\w-]+)/operations/synthese/detail-assurance-vie.html\?idx=(?P<idx>\d+)&famillecode=(?P<category>\d+)',
        LifeInsuranceInvestmentsPage
    )

    netfinca_redirection = URL(
        r'(?P<space>[\w-]+)/operations/moco/catitres/_?jcr[:_]content.init.html', NetfincaRedirectionPage
    )

    predica_redirection = URL(
        r'(?P<space>[\w-]+)/operations/moco/predica/_?jcr[:_]content.init.html', PredicaRedirectionPage
    )

    predica_investments = URL(
        r'https://npcprediweb.predica.credit-agricole.fr/rest/detailEpargne/contrat/', PredicaInvestmentsPage
    )

    profile_page = URL(r'(?P<space>[\w-]+)/operations/synthese/jcr:content.npc.store.client.json', ProfilePage)

    profile_details = URL(
        r'(?P<space>[\w-]+)/operations/profil/infos-personnelles/gerer-coordonnees.html', ProfileDetailsPage
    )

    pro_profile_details = URL(
        r'(?P<space>[\w-]+)/operations/profil/infos-personnelles/controler-coordonnees.html', ProProfileDetailsPage
    )

    recipients = URL('(?P<space>.*)/operations/(?P<op>.*)/virement/jcr:content.accounts.json', RecipientsPage)
    transfer_token = URL(
        '(?P<space>.*)/operations/(?P<op>.*)/virement.npcgeneratetoken.json\?tokenTypeId=1', TransferTokenPage
    )
    transfer = URL('(?P<space>.*)/operations/(?P<op>.*)/virement/jcr:content.check-transfer.json', TransferPage)
    transfer_recap = URL(
        '(?P<space>.*)/operations/(?P<op>.*)/virement/jcr:content.transfer-data.json\?useSession=true', TransferPage
    )
    transfer_exec = URL('(?P<space>.*)/operations/(?P<op>.*)/virement/jcr:content.process-transfer.json', TransferPage)

    def __init__(self, website, *args, **kwargs):
        super(CreditAgricoleBrowser, self).__init__(*args, **kwargs)
        self.website = website
        self.accounts_url = None

        # Netfinca browser:
        self.weboob = kwargs.pop('weboob')
        dirname = self.responses_dirname
        self.netfinca = NetfincaBrowser(
            '', '', logger=self.logger, weboob=self.weboob, responses_dirname=dirname, proxy=self.PROXIES
        )

    @property
    def space(self):
        return self.session.cookies.get('marche', None)

    def deinit(self):
        super(CreditAgricoleBrowser, self).deinit()
        self.netfinca.deinit()

    @retry(BrowserUnavailable)
    def do_security_check(self):
        try:
            form = self.get_security_form()
            self.security_check.go(data=form)
        except ServerError as exc:
            # Wrongpass returns a 500 server error...
            exc_json = exc.response.json()
            error = exc_json.get('error')
            if error:
                message = error.get('message', '')
                wrongpass_messages = ("Votre identification est incorrecte", "Vous n'avez plus droit")
                if any(value in message for value in wrongpass_messages):
                    raise BrowserIncorrectPassword()
                if 'obtenir un nouveau code' in message:
                    raise ActionNeeded(message)

                code = error.get('code', '')
                technical_error_messages = ('Un incident technique', 'identifiant et votre code personnel')
                # Sometimes there is no error message, so we try to use the code as well
                technical_error_codes = ('technical_error',)
                if any(value in message for value in technical_error_messages) or \
                   any(value in code for value in technical_error_codes):
                    raise BrowserUnavailable(message)

            # When a PSD2 SCA is required it also returns a 500, hopefully we can detect it
            if (
                exc_json.get('url') == 'dsp2/informations.html'
                or exc_json.get('redirection', '').endswith('dsp2/informations.html')
            ):
                return self.handle_sca()

            raise

    def do_login(self):
        if not self.username or not self.password:
            raise BrowserIncorrectPassword()

        # For historical reasons (old cragr website), the websites look like 'www.ca-region.fr',
        # from which we extract 'ca-region' to construct the BASEURL with a format such as:
        # 'https://www.credit-agricole.fr/ca-region/'
        region_domain = re.sub(r'^www\.', 'www.credit-agricole.fr/', self.website.replace('.fr', ''))
        self.BASEURL = 'https://%s/' % region_domain

        self.login_page.go()
        self.do_security_check()

        # accounts_url may contain '/particulier', '/professionnel', '/entreprise', '/agriculteur' or '/association'
        self.accounts_url = self.page.get_accounts_url()
        assert self.accounts_url, 'Could not get accounts url from security check'
        try:
            self.location(self.accounts_url)
        except HTTPNotFound:
            # Sometimes the url the json sends us back is just unavailable...
            raise BrowserUnavailable()

        assert self.accounts_page.is_here(), 'We failed to login after the security check: response URL is %s' % self.url
        # Once the security check is passed, we are logged in.

    def handle_sca(self):
        """
        The ActionNeeded is temporary: we are waiting for an account to implement the SCA.
        We can raise an ActionNeed because a validated SCA is cross web browser: if user performs
        the SCA on its side there will be no SCA anymore on weboob.
        """
        raise ActionNeeded('Vous devez réaliser la double authentification sur le portail internet')

    def get_security_form(self):
        headers = {'Referer': self.BASEURL + 'particulier/acceder-a-mes-comptes.html'}
        data = {'user_id': self.username}
        self.keypad.go(headers=headers, data=data)

        keypad_password = self.page.build_password(self.password[:6])
        keypad_id = self.page.get_keypad_id()
        assert keypad_password, 'Could not obtain keypad password'
        assert keypad_id, 'Could not obtain keypad id'
        self.login_page.go()
        # Get the form data to POST the security check:
        form = self.page.get_login_form(self.username, keypad_password, keypad_id)
        return form

    def get_account_iban(self, account_index, account_category, weboob_account_id):
        """
        Fetch an IBAN for a given account
        It may fail from time to time (error 500 or 403)
        """
        params = {
            'compteIdx': int(account_index),
            'grandeFamilleCode': int(account_category),
        }
        try:
            self.account_iban.go(space=self.space, params=params)
        except (ClientError, ServerError):
            self.logger.warning('Request to IBAN failed for account id "%s"', weboob_account_id)
            return NotAvailable

        iban = self.page.get_iban()
        if is_iban_valid(iban):
            return iban
        return NotAvailable

    @need_login
    def check_space_connection(self, contract):
        # Going to a specific space often returns a 500 error
        # so we might have to retry several times.
        try:
            self.go_to_account_space(contract)
        except (ServerError, BrowserUnavailable):
            self.logger.warning('Server returned error 500 when trying to access space %s, we try again', contract)
            try:
                self.go_to_account_space(contract)
            except (ServerError, BrowserUnavailable):
                return False
        return True

    @need_login
    def iter_accounts(self):
        # Determine how many spaces are present on the connection:
        self.location(self.accounts_url)
        if not self.accounts_page.is_here():
            # We have been logged out.
            self.do_login()
        total_spaces = self.page.count_spaces()
        self.logger.info('The total number of spaces on this connection is %s.', total_spaces)

        # Complete accounts list is required to match card parent accounts
        # and to avoid accounts that are present on several spaces
        all_accounts = {}
        deferred_cards = {}

        for contract in range(total_spaces):
            if not self.check_space_connection(contract):
                self.logger.warning(
                    'Server returned error 500 twice when trying to access space %s, this space will be skipped',
                    contract
                )
                continue

            # Some spaces have no main account
            if self.page.has_main_account():
                # The main account is not located at the same place in the JSON.
                main_account = self.page.get_main_account()
                if main_account.balance == NotAvailable:
                    self.check_space_connection(contract)
                    main_account = self.page.get_main_account()
                    if main_account.balance == NotAvailable:
                        self.logger.warning('Could not fetch the balance for main account %s.', main_account.id)
                # Get cards for the main account
                if self.page.has_main_cards():
                    for card in self.page.iter_main_cards():
                        card.parent = main_account
                        card.currency = card.parent.currency
                        card.owner_type = card.parent.owner_type
                        card._category = card.parent._category
                        card._contract = contract
                        deferred_cards[card.id] = card

                main_account._contract = contract
            else:
                main_account = None

            space_type = self.page.get_space_type()
            accounts_list = list(self.page.iter_accounts())
            for account in accounts_list:
                account._contract = contract
            ''' Other accounts have no balance in the main JSON, so we must get all
            the (_id_element_contrat, balance) pairs in the account_details JSON.

            Account categories always correspond to the same account types:
            # Category 1: Checking accounts,
            # Category 2: To be determined,
            # Category 3: Savings,
            # Category 4: Loans & Credits,
            # Category 5: Insurances (skipped),
            # Category 6: To be determined,
            # Category 7: Market accounts. '''

            categories = {int(account._category) for account in accounts_list if account._category not in (None, '5')}
            account_balances = {}
            loan_ids = {}
            for category in categories:
                self.account_details.go(space=self.space, category=category)
                account_balances.update(self.page.get_account_balances())
                loan_ids.update(self.page.get_loan_ids())

            if main_account:
                if main_account.type == Account.TYPE_CHECKING:
                    main_account.iban = self.get_account_iban(main_account._index, 1, main_account.id)

                if main_account.id not in all_accounts:
                    all_accounts[main_account.id] = main_account
                    yield main_account

            for account in accounts_list:
                if empty(account.balance):
                    account.balance = account_balances.get(account._id_element_contrat, NotAvailable)

                if account.type == Account.TYPE_CHECKING:
                    account.iban = self.get_account_iban(account._index, account._category, account.id)

                # Loans have a specific ID that we need to fetch
                # so the backend can match loans properly.
                if account.type in (Account.TYPE_LOAN, Account.TYPE_CONSUMER_CREDIT):
                    account.id = account.number = loan_ids.get(account._id_element_contrat, account.id)
                    if empty(account.balance):
                        self.logger.warning(
                            'Loan skip: no balance is available for %s, %s account', account.id, account.label
                        )
                        continue
                    account = self.switch_account_to_loan(account)

                elif account.type == Account.TYPE_REVOLVING_CREDIT:
                    account.id = account.number = loan_ids.get(account._id_element_contrat, account.id)
                    account = self.switch_account_to_revolving(account)

                elif account.type == Account.TYPE_PER:
                    account = self.switch_account_to_per(account)

                if account.id not in all_accounts:
                    all_accounts[account.id] = account
                    yield account
            ''' Fetch all deferred credit cards for this space: from the space type
            we must determine the required URL parameters to build the cards URL.
            If there is no card on the space, the server will return a 500 error
            (it is the same on the website) so we must handle it with try/except. '''
            cards_parameters = {
                'PARTICULIER': ('particulier', 'moyens-paiement'),
                'HORS_MARCHE': ('particulier', 'moyens-paiement'),
                'PROFESSIONNEL': ('professionnel', 'paiements-encaissements'),
                'AGRICULTEUR': ('agriculteur', 'paiements-encaissements'),
                'ASSOC_CA_MODERE': ('association', 'paiements-encaissements'),
                'ENTREPRISE': ('entreprise', 'paiements-encaissements'),
                'PROFESSION_LIBERALE': ('professionnel', 'paiements-encaissements'),
                'PROMOTEURS': ('professionnel', 'paiements-encaissements'),
            }
            assert space_type in cards_parameters, 'Space type %s has never been encountered before.' % space_type

            space, op = cards_parameters[space_type]
            if 'banque-privee' in self.url:
                # The first parameter will always be 'banque-privee'.
                space = 'banque-privee'

            # The card request often fails, even on the website,
            # so we try twice just in case we fail to get there:
            for trial in range(2):
                try:
                    self.check_space_connection(contract)
                    self.cards.go(space=space, op=op)
                except (ServerError, ClientError, HTTPNotFound):
                    if trial == 0:
                        self.logger.warning('Request to cards failed, we try again.')
                    else:
                        self.logger.warning('Request to cards failed twice, the cards of this space will be skipped.')
                else:
                    break

            if self.cards.is_here():
                for card in self.page.iter_card_parents():
                    if card.id not in deferred_cards:
                        card.number = card.id
                        card.parent = all_accounts.get(card._parent_id, NotAvailable)
                        card.currency = card.parent.currency
                        card.owner_type = card.parent.owner_type
                        card._category = card.parent._category
                        card._contract = contract
                        deferred_cards[card.id] = card

        # We must check if cards are unique on their parent account;
        # if not, we cannot retrieve their summaries in iter_history.
        parent_accounts = []
        for card in deferred_cards.values():
            parent_accounts.append(card.parent.id)
        for card in deferred_cards.values():
            if parent_accounts.count(card.parent.id) == 1:
                card._unique = True
            else:
                card._unique = False
            yield card

    def switch_account_to_loan(self, account):
        loan = Loan()
        copy_attrs = (
            'id',
            'number',
            'label',
            'type',
            'currency',
            '_index',
            '_category',
            '_contract',
            '_id_element_contrat',
            'owner_type'
        )
        for attr in copy_attrs:
            setattr(loan, attr, getattr(account, attr))
        loan.balance = -account.balance
        return loan

    def switch_account_to_revolving(self, account):
        loan = Loan()
        copy_attrs = (
            'id',
            'number',
            'label',
            'type',
            'currency',
            '_index',
            '_category',
            '_contract',
            '_id_element_contrat',
            'owner_type'
        )
        for attr in copy_attrs:
            setattr(loan, attr, getattr(account, attr))
        loan.balance = Decimal(0)
        loan.available_amount = account.balance
        return loan

    def switch_account_to_per(self, account):
        per = Per.from_dict(account.to_dict())
        copy_attrs = (
            '_index',
            '_category',
            '_contract',
            '_id_element_contrat',
        )
        for attr in copy_attrs:
            setattr(per, attr, getattr(account, attr))

        if per.label == 'PER Assurance':
            per.provider_type = PerProviderType.INSURER
        else:
            per.provider_type = PerProviderType.BANK

        # No available information concerning PER version
        return per

    @need_login
    def go_to_account_space(self, contract):
        # This request often returns a 500 error on this quality website
        for tries in range(4):
            try:
                self.contracts_page.go(space=self.space, id_contract=contract)
            except ServerError as e:
                if e.response.status_code == 500:
                    self.logger.warning('Space switch returned a 500 error, try again.')
                    self.contracts_page.go(space=self.space, id_contract=contract)
                else:
                    raise
            if not self.accounts_page.is_here():
                self.logger.warning('We have been loggged out, relogin.')
                self.do_login()
            else:
                return
            if tries >= 3:
                raise BrowserUnavailable()

    @need_login
    def iter_history(self, account, coming=False):
        if account.type == Account.TYPE_CARD:
            card_transactions = []
            self.go_to_account_space(account._contract)
            # Deferred cards transactions have a specific JSON.
            # Only three months of history available for cards.
            value = 0 if coming else 1
            params = {
                'grandeFamilleCode': int(account._category),
                'compteIdx': int(account.parent._index),
                'carteIdx': int(account._index),
                'rechercheEncoursDebite': value
            }
            self.card_history.go(space=self.space, params=params)
            for tr in self.page.iter_card_history():
                card_transactions.append(tr)

            # If the card if not unique on the parent id, it is impossible
            # to know which summary corresponds to which card.
            if not coming and card_transactions and account._unique:
                # Get card summaries from parent account
                # until we reach the oldest card transaction
                last_transaction = card_transactions[-1]
                before_last_transaction = False
                params = {
                    'compteIdx': int(account.parent._index),
                    'grandeFamilleCode': int(account.parent._category),
                    'idDevise': str(account.parent.currency),
                    'idElementContrat': str(account.parent._id_element_contrat),
                }
                self.history.go(space=self.space, params=params)
                for tr in self.page.iter_history():
                    if tr.date < last_transaction.date:
                        before_last_transaction = True
                        break
                    if tr.type == Transaction.TYPE_CARD_SUMMARY:
                        tr.amount = -tr.amount
                        card_transactions.append(tr)

                while self.page.has_next_page() and not before_last_transaction:
                    next_index = self.page.get_next_index()
                    params = {
                        'grandeFamilleCode': int(account.parent._category),
                        'compteIdx': int(account.parent._index),
                        'idDevise': str(account.parent.currency),
                        'startIndex': next_index,
                        'count': 100,
                    }
                    self.history.go(space=self.space, params=params)
                    for tr in self.page.iter_history():
                        if tr.date < last_transaction.date:
                            before_last_transaction = True
                            break
                        if tr.type == Transaction.TYPE_CARD_SUMMARY:
                            tr.amount = -tr.amount
                            card_transactions.append(tr)

            for tr in sorted_transactions(card_transactions):
                yield tr
            return

        # These three parameters are required to get the transactions for non_card accounts
        if (
            empty(account._index) or empty(account._category) or empty(account._id_element_contrat)
            or account.type == Account.TYPE_CONSUMER_CREDIT
        ):
            return

        self.go_to_account_space(account._contract)
        params = {
            'compteIdx': int(account._index),
            'grandeFamilleCode': int(account._category),
            'idDevise': str(account.currency),
            'idElementContrat': str(account._id_element_contrat),
        }
        # This request might lead to occasional 500 errors
        for trial in range(2):
            try:
                self.history.go(space=self.space, params=params)
            except ServerError:
                self.logger.warning('Request to get account history failed.')
            else:
                break

        if not self.history.is_here():
            raise BrowserUnavailable()

        for tr in self.page.iter_history():
            # For "Livret A", value dates of transactions are always
            # 1st or 15th of the month so we specify a valuation date.
            # Example: rdate = 21/02, date=01/02 then vdate = 01/02.
            if account.type == Account.TYPE_SAVINGS:
                tr.vdate = tr.date
            yield tr

        # Get other transactions 100 by 100:
        while self.page.has_next_page():
            next_index = self.page.get_next_index()
            params = {
                'grandeFamilleCode': int(account._category),
                'compteIdx': int(account._index),
                'idDevise': str(account.currency),
                'startIndex': next_index,
                'count': 100,
            }
            self.history.go(space=self.space, params=params)
            for tr in self.page.iter_history():
                yield tr

    @need_login
    def iter_investment(self, account):
        if (
            account.type == Account.TYPE_LIFE_INSURANCE
            and ('rothschild' in account.label.lower() or re.match(r'^open (perspective|strat)', account.label, re.I))
        ):
            self.life_insurance_investments.go(space=self.space, idx=account._index, category=account._category)
            # TODO
            #for inv in self.page.iter_investments():
            #    yield inv

        elif account.type in (
            Account.TYPE_PER,
            Account.TYPE_PERP,
            Account.TYPE_PERCO,
            Account.TYPE_LIFE_INSURANCE,
            Account.TYPE_CAPITALISATION
        ):
            if account.label == "Vers l'avenir":
                # Website crashes when clicking on these Life Insurances...
                return

            self.go_to_account_space(account._contract)
            token = self.token_page.go().get_token()
            data = {
                'situation_travail': 'CONTRAT',
                'idelco': account.id,
                ':cq_csrf_token': token,
            }
            try:
                self.predica_redirection.go(space=self.space, data=data)
            except ServerError:
                self.logger.warning('Got ServerError when fetching investments for account id %s', account.id)
            else:
                self.predica_investments.go()
                for inv in self.page.iter_investments():
                    yield inv

        elif account.type == Account.TYPE_PEA and account.label == 'Compte espèce PEA':
            yield create_french_liquidity(account.balance)
            return

        elif account.type in (Account.TYPE_PEA, Account.TYPE_MARKET):
            # Do not try to get to Netfinca if there is no money
            # on the account or the server will return an error 500
            if account.balance == 0:
                return
            self.go_to_account_space(account._contract)
            token = self.token_page.go().get_token()
            data = {
                'situation_travail': 'BANCAIRE',
                'num_compte': account.id,
                'code_fam_produit': account._fam_product_code,
                'code_fam_contrat_compte': account._fam_contract_code,
                ':cq_csrf_token': token,
            }

            # For some market accounts, investments are not even accessible,
            # and the only way to know if there are investments is to try
            # to go to the Netfinca space with the accounts parameters.
            try:
                self.netfinca_redirection.go(space=self.space, data=data)
            except BrowserHTTPNotFound:
                self.logger.info('Investments are not available for this account.')
                self.go_to_account_space(account._contract)
                return
            url = self.page.get_url()
            if 'netfinca' in url:
                self.location(url)
                self.netfinca.session.cookies.update(self.session.cookies)
                self.netfinca.accounts.go()
                for inv in self.netfinca.iter_investments(account):
                    if inv.code == 'XX-liquidity' and account.type == Account.TYPE_PEA:
                        # Liquidities are already fetched on the "PEA espèces"
                        continue
                    yield inv

    @need_login
    def iter_advisor(self):
        self.go_to_account_space(0)
        owner_type = self.page.get_owner_type()
        self.profile_page.go(space=self.space)
        if owner_type == 'PRIV':
            advisor = self.page.get_advisor()
            self.profile_details.go(space=self.space)
            self.page.fill_advisor(obj=advisor)
            yield advisor
        elif owner_type == 'ORGA':
            advisor = self.page.get_advisor()
            self.pro_profile_details.go(space=self.space)
            self.page.fill_advisor(obj=advisor)
            yield advisor

    @need_login
    def get_profile(self):
        # There is one profile per space, so we only fetch the first one
        self.go_to_account_space(0)
        owner_type = self.page.get_owner_type()
        self.profile_page.go(space=self.space)
        if owner_type == 'PRIV':
            profile = self.page.get_user_profile()
            self.profile_details.go(space=self.space)
            self.page.fill_profile(obj=profile)
            return profile
        elif owner_type == 'ORGA':
            profile = self.page.get_company_profile()
            self.pro_profile_details.go(space=self.space)
            self.page.fill_profile(obj=profile)
            return profile

    @need_login
    def get_account_transfer_space_info(self, account):
        self.go_to_account_space(account._contract)

        connection_id = self.page.get_connection_id()

        operations = {
            'particulier': 'moyens-paiement',
            'professionnel': 'paiements-encaissements',
            'association': 'paiements-encaissements',
            'entreprise': 'paiements-encaissements',
            'banque-privee': 'moyens-paiement',
            'agriculteur': 'paiements-encaissements',
            'promoteurs': 'paiements-encaissements',
        }

        referer = self.absurl('/%s/operations/%s/virement.html.html' % (self.space, operations[self.space]))

        return self.space, operations[self.space], referer, connection_id

    @need_login
    def iter_debit_accounts(self):
        assert self.recipients.is_here()
        for index, debit_accounts in enumerate(self.page.iter_debit_accounts()):
            debit_accounts._index = index
            if self.page.is_sender_account(debit_accounts.id):
                # only yield able to do transfer accounts
                yield debit_accounts

    @need_login
    def iter_transfer_recipients(self, account, transfer_space_info=None):
        if account.type in (
            account.TYPE_CARD,
            account.TYPE_LOAN,
            account.TYPE_LIFE_INSURANCE,
            account.TYPE_PEA,
            account.TYPE_CONSUMER_CREDIT,
            account.TYPE_REVOLVING_CREDIT,
        ):
            return

        # avoid to call `get_account_transfer_space_info()` several time
        if transfer_space_info:
            space, operation, referer = transfer_space_info
        else:
            space, operation, referer, _ = self.get_account_transfer_space_info(account)

        self.go_to_account_space(account._contract)
        self.recipients.go(space=space, op=operation, headers={'Referer': referer})

        if not self.page.is_sender_account(account.id):
            return

        # can't use 'ignore_duplicate' in DictElement because we need the 'index' to do transfer
        seen = set()
        seen.add(account.id)

        for index, internal_rcpt in enumerate(self.page.iter_internal_recipient()):
            internal_rcpt._index = index
            if internal_rcpt._is_recipient and (internal_rcpt.id not in seen):
                seen.add(internal_rcpt.id)
                yield internal_rcpt

        for index, external_rcpt in enumerate(self.page.iter_external_recipient()):
            external_rcpt._index = index
            if external_rcpt.id not in seen:
                seen.add(external_rcpt.id)
                yield external_rcpt

    @need_login
    def init_transfer(self, transfer, **params):
        # first, get _account on account list to get recipient
        _account = strict_find_object(self.iter_accounts(), id=transfer.account_id, error=AccountNotFound)

        # get information to go on transfer page
        space, operation, referer, connection_id = self.get_account_transfer_space_info(account=_account)

        recipient = strict_find_object(
            self.iter_transfer_recipients(_account, transfer_space_info=(space, operation, referer)),
            id=transfer.recipient_id,
            error=RecipientNotFound
        )
        # Then, get account on transfer account list to get index and other information
        account = strict_find_object(self.iter_debit_accounts(), id=_account.id, error=AccountNotFound)

        # get token and transfer token to init transfer
        token = self.token_page.go().get_token()
        transfer_token = self.transfer_token.go(space=space, op=operation, headers={'Referer': referer}).get_token()

        if transfer.label:
            label = transfer.label[:33].encode('ISO-8859-15', errors='ignore').decode('ISO-8859-15')
            transfer.label = re.sub(r'[+!]', '', label)

        data = {
            'connexionId': connection_id,
            'cr': self.session.cookies['caisse-regionale'],
            'creditAccountIban': recipient.iban,
            'creditAccountIndex': recipient._index,
            'debitAccountIndex': account._index,
            'debitAccountNumber': account.number,
            'externalAccount': recipient.category == 'Externe',
            'recipientName': recipient.label,
            'transferAmount': transfer.amount,
            'transferComplementaryInformation1': transfer.label,
            'transferComplementaryInformation2': '',
            'transferComplementaryInformation3': '',
            'transferComplementaryInformation4': '',
            'transferCurrencyCode': account.currency,
            'transferDate': transfer.exec_date.strftime('%d/%m/%Y'),
            'transferFrequency': 'U',
            'transferRef': transfer.label,
            'transferType': 'UNIQUE',
            'typeCompte': account.label,
        }

        # update transfer data according to recipient category
        if recipient.category == 'Interne':
            data['creditAccountNumber'] = recipient.id
            data['recipientName'] = recipient._owner_name

        # init transfer request
        self.transfer.go(
            space=space,
            op=operation,
            headers={
                'Referer': referer,
                'CSRF-Token': token,
                'NPC-Generated-Token': transfer_token,
            },
            json=data
        )
        assert self.page.check_transfer()
        # get recap because it's not returned by init transfer request
        self.transfer_recap.go(
            space=space,
            op=operation,
            headers={'Referer': self.absurl('/%s/operations/%s/virement.postredirect.html' % (space, operation))}
        )
        # information needed to exec transfer
        transfer._space = space
        transfer._operation = operation
        transfer._token = token
        transfer._connection_id = connection_id
        return self.page.handle_response(transfer)

    @need_login
    def execute_transfer(self, transfer, **params):
        self.transfer_exec.go(
            space=transfer._space,
            op=transfer._operation,
            headers={
                'Referer': self.absurl(
                    '/%s/operations/%s/virement.postredirect.html' % (transfer._space, transfer._operation)
                ),
                'CSRF-Token': transfer._token,
            },
            json={'connexionId': transfer._connection_id}
        )
        assert self.page.check_transfer_exec()
        return transfer

    @need_login
    def build_recipient(self, recipient):
        raise BrowserUnavailable()

    @need_login
    def new_recipient(self, recipient, **params):
        raise BrowserUnavailable()

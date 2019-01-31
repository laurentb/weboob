# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019 Romain Bignon
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


from __future__ import unicode_literals

from decimal import Decimal
import re

from weboob.capabilities.bank import Account, Transaction
from weboob.capabilities.base import empty, NotAvailable
from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserUnavailable, BrowserIncorrectPassword, ActionNeeded
from weboob.browser.exceptions import ServerError, BrowserHTTPNotFound
from weboob.capabilities.bank import Loan
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    LoginPage, LoggedOutPage, KeypadPage, SecurityPage, ContractsPage, FirstConnectionPage, AccountsPage, AccountDetailsPage,
    TokenPage, IbanPage, HistoryPage, CardsPage, CardHistoryPage, NetfincaRedirectionPage, PredicaRedirectionPage,
    PredicaInvestmentsPage, ProfilePage, ProfileDetailsPage, ProProfileDetailsPage,
)

from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .netfinca_browser import NetfincaBrowser


__all__ = ['CragrAPI']


class CragrAPI(LoginBrowser):
    login_page = URL(r'particulier/acceder-a-mes-comptes.html$', LoginPage)
    keypad = URL(r'particulier/acceder-a-mes-comptes.authenticationKeypad.json', KeypadPage)
    security_check = URL(r'particulier/acceder-a-mes-comptes.html/j_security_check', SecurityPage)
    first_connection = URL(r'.*/operations/interstitielles/premiere-connexion.html', FirstConnectionPage)
    logged_out = URL(r'.*', LoggedOutPage)

    token_page = URL(r'libs/granite/csrf/token.json', TokenPage)

    contracts_page = URL(r'particulier/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)',
                         r'association/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)',
                         r'professionnel/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)',
                         r'entreprise/operations/.rechargement.contexte.html\?idBamIndex=(?P<id_contract>)', ContractsPage)

    accounts_page = URL(r'particulier/operations/synthese.html',
                        r'association/operations/synthese.html',
                        r'professionnel/operations/synthese.html',
                        r'entreprise/operations/synthese.html', AccountsPage)

    account_details = URL(r'particulier/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
                          r'association/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
                          r'professionnel/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)',
                          r'entreprise/operations/synthese/jcr:content.produits-valorisation.json/(?P<category>)', AccountDetailsPage)

    account_iban = URL(r'particulier/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json',
                       r'association/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json',
                       r'professionnel/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json',
                       r'entreprise/operations/operations-courantes/editer-rib/jcr:content.ibaninformation.json', IbanPage)

    cards = URL(r'particulier/operations/moyens-paiement/mes-cartes/jcr:content.listeCartesParCompte.json',
                r'association/operations/moyens-paiement/mes-cartes/jcr:content.listeCartesParCompte.json',
                r'professionnel/operations/moyens-paiement/mes-cartes/jcr:content.listeCartesParCompte.json',
                r'entreprise/operations/moyens-paiement/mes-cartes/jcr:content.listeCartesParCompte.json', CardsPage)

    history = URL(r'particulier/operations/synthese/detail-comptes/jcr:content.n3.operations.json',
                  r'association/operations/synthese/detail-comptes/jcr:content.n3.operations.json',
                  r'professionnel/operations/synthese/detail-comptes/jcr:content.n3.operations.json',
                  r'entreprise/operations/synthese/detail-comptes/jcr:content.n3.operations.json', HistoryPage)

    card_history = URL(r'particulier/operations/synthese/detail-comptes/jcr:content.n3.operations.encours.carte.debit.differe.json',
                       r'association/operations/synthese/detail-comptes/jcr:content.n3.operations.encours.carte.debit.differe.json',
                       r'professionnel/operations/synthese/detail-comptes/jcr:content.n3.operations.encours.carte.debit.differe.json',
                       r'entreprise/operations/synthese/detail-comptes/jcr:content.n3.operations.encours.carte.debit.differe.json', CardHistoryPage)

    netfinca_redirection = URL(r'particulier/operations/moco/catitres/jcr:content.init.html',
                               r'association/operations/moco/catitres/jcr:content.init.html',
                               r'professionnel/operations/moco/catitres/jcr:content.init.html',
                               r'entreprise/operations/moco/catitres/jcr:content.init.html',
                               r'particulier/operations/moco/catitres/_jcr_content.init.html',
                               r'association/operations/moco/catitres/_jcr_content.init.html',
                               r'professionnel/operations/moco/catitres/_jcr_content.init.html',
                               r'entreprise/operations/moco/catitres/_jcr_content.init.html', NetfincaRedirectionPage)

    predica_redirection = URL(r'particulier/operations/moco/predica/jcr:content.init.html',
                              r'association/operations/moco/predica/jcr:content.init.html',
                              r'professionnel/operations/moco/predica/jcr:content.init.html',
                              r'entreprise/operations/moco/predica/jcr:content.init.html', PredicaRedirectionPage)

    predica_investments = URL(r'https://npcprediweb.predica.credit-agricole.fr/rest/detailEpargne/contrat/', PredicaInvestmentsPage)

    profile_page = URL(r'particulier/operations/synthese/jcr:content.npc.store.client.json',
                       r'association/operations/synthese/jcr:content.npc.store.client.json',
                       r'professionnel/operations/synthese/jcr:content.npc.store.client.json',
                       r'entreprise/operations/synthese/jcr:content.npc.store.client.json', ProfilePage)

    profile_details = URL(r'particulier/operations/profil/infos-personnelles/gerer-coordonnees.html', ProfileDetailsPage)

    pro_profile_details = URL(r'association/operations/profil/infos-personnelles/controler-coordonnees.html',
                              r'professionnel/operations/profil/infos-personnelles/controler-coordonnees.html',
                              r'entreprise/operations/profil/infos-personnelles/controler-coordonnees.html', ProProfileDetailsPage)

    def __init__(self, website, *args, **kwargs):
        super(CragrAPI, self).__init__(*args, **kwargs)
        website = website.replace('.fr', '')
        self.region = re.sub('^m\.', 'www.credit-agricole.fr/', website)
        self.BASEURL = 'https://%s/' % self.region
        self.accounts_url = None

        # Netfinca browser:
        self.weboob = kwargs.pop('weboob')
        dirname = self.responses_dirname
        self.netfinca = NetfincaBrowser('', '', logger=self.logger, weboob=self.weboob, responses_dirname=dirname, proxy=self.PROXIES)

    def deinit(self):
        super(CragrAPI, self).deinit()
        self.netfinca.deinit()

    def do_login(self):
        form = self.get_security_form()
        try:
            self.security_check.go(data=form)
        except ServerError as exc:
            # Wrongpass returns a 500 server error...
            error = exc.response.json().get('error')
            if error:
                message = error.get('message', '')
                if 'Votre identification est incorrecte' in message:
                    raise BrowserIncorrectPassword()
                if 'obtenir un nouveau code' in message:
                    raise ActionNeeded(message)
                technical_errors = ('Un incident technique', 'identifiant et votre code personnel')
                if any(value in message for value in technical_errors):
                    # If it is a technical error, we try login again
                    form = self.get_security_form()
                    try:
                        self.security_check.go(data=form)
                    except ServerError as exc:
                        error = exc.response.json().get('error')
                        if error:
                            message = error.get('message', '')
                            if 'Un incident technique' in message:
                                raise BrowserUnavailable(message)
                assert False, 'Unhandled Server Error encountered: %s' % error.get('message', '')

        # accounts_url may contain '/particulier', '/professionnel' or '/association'
        self.accounts_url = self.page.get_accounts_url()
        assert self.accounts_url, 'Could not get accounts url from security check'
        self.location(self.accounts_url)
        assert self.accounts_page.is_here(), 'We failed to login after the security check!'
        # Once the security check is passed, we are logged in.

    def get_security_form(self):
        self.keypad.go()
        keypad_password = self.page.build_password(self.password[:6])
        keypad_id = self.page.get_keypad_id()
        assert keypad_password, 'Could not obtain keypad password'
        assert keypad_id, 'Could not obtain keypad id'
        self.login_page.go()
        # Get the form data to POST the security check:
        form = self.page.get_login_form(self.username, keypad_password, keypad_id)
        return form

    @need_login
    def get_accounts_list(self):
        # Determine how many spaces are present on the connection:
        self.location(self.accounts_url)
        if not self.accounts_page.is_here():
            # We have been logged out.
            self.do_login()
        total_spaces = self.page.count_spaces()
        self.logger.info('The total number of spaces on this connection is %s.' % total_spaces)

        # Complete accounts list is required to match card parent accounts
        # and to avoid accounts that are present on several spaces
        all_accounts = {}
        deferred_cards = {}

        for contract in range(total_spaces):
            # This request often returns a 500 error so we retry several times.
            try:
                self.contracts_page.go(id_contract=contract)
            except ServerError:
                self.logger.warning('Server returned error 500 when trying to access space %s, we try again' % contract)
                try:
                    self.contracts_page.go(id_contract=contract)
                except ServerError:
                    self.logger.warning('Server returned error 500 twice when trying to access space %s, this space will be skipped' % contract)
                    continue

            # The main account is not located at the same place in the JSON.
            main_account = self.page.get_main_account()
            main_account.owner_type = self.page.get_owner_type()
            main_account._contract = contract

            accounts_list = list(self.page.iter_accounts())
            for account in accounts_list:
                account._contract = contract
                account.owner_type = self.page.get_owner_type()

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
                self.account_details.go(category=category)
                account_balances.update(self.page.get_account_balances())
                loan_ids.update(self.page.get_loan_ids())

            if main_account.type == Account.TYPE_CHECKING:
                params = {
                    'compteIdx': int(main_account._index),
                    'grandeFamilleCode': 1,
                }
                self.account_iban.go(params=params)
                iban = self.page.get_iban()
                if is_iban_valid(iban):
                    main_account.iban = iban
            if main_account.id not in all_accounts:
                all_accounts[main_account.id] = main_account
                yield main_account

            for account in accounts_list:
                if empty(account.balance):
                    account.balance = account_balances.get(account._id_element_contrat, NotAvailable)
                if account.type == Account.TYPE_CHECKING:
                    params = {
                        'compteIdx': int(account._index),
                        'grandeFamilleCode': int(account._category),
                    }
                    self.account_iban.go(params=params)
                    iban = self.page.get_iban()
                    if is_iban_valid(iban):
                        account.iban = iban

                # Loans have a specific ID that we need to fetch
                # so the backend can match loans properly.
                if account.type == Account.TYPE_LOAN:
                    account.id = account.number = loan_ids.get(account._id_element_contrat, account.id)
                    account = self.switch_account_to_loan(account)
                elif account.type == Account.TYPE_REVOLVING_CREDIT:
                    account.id = account.number = loan_ids.get(account._id_element_contrat, account.id)
                    account = self.switch_account_to_revolving(account)
                if account.id not in all_accounts:
                    all_accounts[account.id] = account
                    yield account

            # Fetch all deferred credit cards for this space
            self.cards.go()
            for card in self.page.iter_card_parents():
                card.number = card.id
                card.parent = all_accounts.get(card._parent_id, NotAvailable)
                card.currency = card.parent.currency
                card.owner_type = card.parent.owner_type
                card._category = card.parent._category
                card._contract = contract
                if card.id not in deferred_cards:
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
        copy_attrs = ('id', 'number', 'label', 'type', 'currency', '_index', '_category', '_contract', '_id_element_contrat', 'owner_type')
        for attr in copy_attrs:
            setattr(loan, attr, getattr(account, attr))
        loan.balance = -account.balance
        return loan

    def switch_account_to_revolving(self, account):
        loan = Loan()
        copy_attrs = ('id', 'number', 'label', 'type', 'currency', '_index', '_category', '_contract', '_id_element_contrat', 'owner_type')
        for attr in copy_attrs:
            setattr(loan, attr, getattr(account, attr))
        loan.balance = Decimal(0)
        loan.available_amount = account.balance
        return loan

    @need_login
    def go_to_account_space(self, contract):
        self.contracts_page.go(id_contract=contract)
        if not self.accounts_page.is_here():
            # We have been logged out.
            self.do_login()
            self.contracts_page.go(id_contract=contract)
            assert self.accounts_page.is_here()

    @need_login
    def get_history(self, account, coming=False):
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
            self.card_history.go(params=params)
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
                self.history.go(params=params)
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
                    self.history.go(params=params)
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
        if empty(account._index) or empty(account._category) or empty(account._id_element_contrat):
            return

        self.go_to_account_space(account._contract)
        params = {
            'compteIdx': int(account._index),
            'grandeFamilleCode': int(account._category),
            'idDevise': str(account.currency),
            'idElementContrat': str(account._id_element_contrat),
        }
        self.history.go(params=params)
        for tr in self.page.iter_history():
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
            self.history.go(params=params)
            for tr in self.page.iter_history():
                yield tr

    @need_login
    def iter_investment(self, account):
        if account.type in (Account.TYPE_PERP, Account.TYPE_PERCO, Account.TYPE_LIFE_INSURANCE, Account.TYPE_CAPITALISATION):
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
            self.predica_redirection.go(data=data)
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
                self.netfinca_redirection.go(data=data)
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
        self.contracts_page.go(id_contract=0)
        owner_type = self.page.get_owner_type()
        self.profile_page.go()
        if owner_type == 'PRIV':
            advisor = self.page.get_advisor()
            self.profile_details.go()
            self.page.fill_advisor(obj=advisor)
            return advisor
        elif owner_type == 'ORGA':
            advisor = self.page.get_advisor()
            self.pro_profile_details.go()
            self.page.fill_advisor(obj=advisor)
            return advisor

    @need_login
    def get_profile(self):
        # There is one profile per space, so we only fetch the first one
        self.contracts_page.go(id_contract=0)
        owner_type = self.page.get_owner_type()
        self.profile_page.go()
        if owner_type == 'PRIV':
            profile = self.page.get_user_profile()
            self.profile_details.go()
            self.page.fill_profile(obj=profile)
            return profile
        elif owner_type == 'ORGA':
            profile = self.page.get_company_profile()
            self.pro_profile_details.go()
            self.page.fill_profile(obj=profile)
            return profile

    @need_login
    def iter_transfer_recipients(self, account):
        raise BrowserUnavailable()

    @need_login
    def init_transfer(self, transfer, **params):
        raise BrowserUnavailable()

    @need_login
    def execute_transfer(self, transfer, **params):
        raise BrowserUnavailable()

    @need_login
    def build_recipient(self, recipient):
        raise BrowserUnavailable()

    @need_login
    def new_recipient(self, recipient, **params):
        raise BrowserUnavailable()

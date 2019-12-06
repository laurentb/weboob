# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012  Romain Bignon, Pierre Mazière
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
from datetime import datetime, timedelta, date
from functools import wraps

from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.browser.exceptions import ServerError
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.bank import (
    Account, AddRecipientBankError, AddRecipientStep, Recipient, AccountOwnerType,
    AccountOwnership,
)
from weboob.capabilities.base import find_object
from weboob.tools.capabilities.bank.investments import create_french_liquidity
from weboob.tools.compat import basestring, urlsplit, unicode
from weboob.tools.value import Value

from .pages import (
    LoginPage, AccountsPage, AccountHistoryPage, ContractsPage, ContractsChoicePage, BoursePage,
    AVPage, AVDetailPage, DiscPage, NoPermissionPage, RibPage, HomePage, LoansPage, TransferPage,
    AddRecipientPage, RecipientPage, RecipConfirmPage, SmsPage, RecipRecapPage, LoansProPage,
    Form2Page, DocumentsPage, ClientPage, SendTokenPage, CaliePage, ProfilePage, DepositPage,
    AVHistoryPage, AVInvestmentsPage, CardsPage, AVListPage, CalieContractsPage,
)


__all__ = ['LCLBrowser', 'LCLProBrowser', 'ELCLBrowser']


# Browser
class LCLBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://particuliers.secure.lcl.fr'
    STATE_DURATION = 15

    login = URL(
        r'/outil/UAUT\?from=/outil/UWHO/Accueil/',
        r'/outil/UAUT\?from=.*',
        r'/outil/UWER/Accueil/majicER',
        r'/outil/UWER/Enregistrement/forwardAcc',
        LoginPage)
    contracts_page = URL(
        r'/outil/UAUT/Contrat/choixContrat.*',
        r'/outil/UAUT/Contract/getContract.*',
        r'/outil/UAUT/Contract/selectContracts.*',
        r'/outil/UAUT/Accueil/preRoutageLogin',
        ContractsPage)
    contracts_choice = URL(r'.*outil/UAUT/Contract/routing', ContractsChoicePage)
    home = URL(r'/outil/UWHO/Accueil/', HomePage)
    accounts = URL(r'/outil/UWSP/Synthese', AccountsPage)
    client = URL(r'/outil/uwho', ClientPage)
    history = URL(
        r'/outil/UWLM/ListeMouvements.*/accesListeMouvements.*',
        r'/outil/UWLM/DetailMouvement.*/accesDetailMouvement.*',
        r'/outil/UWLM/Rebond',
        AccountHistoryPage)
    rib = URL(
        r'/outil/UWRI/Accueil/detailRib',
        r'/outil/UWRI/Accueil/listeRib',
        RibPage)
    finalrib = URL(r'/outil/UWRI/Accueil/', RibPage)

    cards = URL(
        r'/outil/UWCB/UWCBEncours.*/listeCBCompte.*',
        r'/outil/UWCB/UWCBEncours.*/listeOperations.*',
        CardsPage)

    skip = URL(
        r'/outil/UAUT/Contrat/selectionnerContrat.*',
        r'/index.html')

    no_perm = URL(r'/outil/UAUT/SansDroit/affichePageSansDroit.*', NoPermissionPage)

    bourse = URL(
        r'https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.synthesis.HomeSynthesis',
        r'https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.account.*',
        r'/outil/UWBO.*',
        BoursePage)

    disc = URL(
        r'https://bourse.secure.lcl.fr/netfinca-titres/servlet/com.netfinca.frontcr.login.ContextTransferDisconnect',
        r'https://assurance-vie-et-prevoyance.secure.lcl.fr/filiale/entreeBam\?.*\btypeaction=reroutage_retour\b',
        r'https://assurance-vie-et-prevoyance.secure.lcl.fr/filiale/ServletReroutageCookie',
        r'/outil/UAUT/RetourPartenaire/retourCar',
        DiscPage)

    form2 = URL(r'/outil/UWVI/Routage', Form2Page)
    send_token = URL(r'/outil/UWVI/AssuranceVie/envoyerJeton', SendTokenPage)
    calie_detail = URL(
        r'https://www.my-calie.fr/FO.HoldersWebSite/Disclaimer/Disclaimer.aspx.*',
        r'https://www.my-calie.fr/FO.HoldersWebSite/Contract/ContractDetails.aspx.*',
        r'https://www.my-calie.fr/FO.HoldersWebSite/Contract/ContractOperations.aspx.*',
        CaliePage)
    calie_contracts = URL(r'https://www.my-calie.fr/FO.HoldersWebSite/Contract/SearchContract.aspx', CalieContractsPage)

    assurancevie = URL(
        r'/outil/UWVI/AssuranceVie/accesSynthese',
        r'/outil/UWVI/AssuranceVie/accesDetail.*',
        AVPage)

    av_list = URL(r'https://assurance-vie-et-prevoyance.secure.lcl.fr/rest/assurance/synthesePartenaire', AVListPage)
    avdetail = URL(r'https://assurance-vie-et-prevoyance.secure.lcl.fr/consultation/epargne', AVDetailPage)
    av_history = URL(r'https://assurance-vie-et-prevoyance.secure.lcl.fr/rest/assurance/historique', AVHistoryPage)
    av_investments = URL(r'https://assurance-vie-et-prevoyance.secure.lcl.fr/rest/detailEpargne/contrat/(?P<life_insurance_id>\w+)', AVInvestmentsPage)

    loans = URL(r'/outil/UWCR/SynthesePar/', LoansPage)
    loans_pro = URL(r'/outil/UWCR/SynthesePro/', LoansProPage)

    transfer_page = URL(r'/outil/UWVS/', TransferPage)
    confirm_transfer = URL(r'/outil/UWVS/Accueil/redirectView', TransferPage)
    recipients = URL(r'/outil/UWBE/Consultation/list', RecipientPage)
    add_recip = URL(r'/outil/UWBE/Creation/creationSaisie', AddRecipientPage)
    recip_confirm = URL(r'/outil/UWBE/Creation/creationConfirmation', RecipConfirmPage)
    send_sms = URL(r'/outil/UWBE/Otp/envoiCodeOtp\?telChoisi=MOBILE', '/outil/UWBE/Otp/getValidationCodeOtp\?codeOtp', SmsPage)
    recip_recap = URL(r'/outil/UWBE/Creation/executeCreation', RecipRecapPage)
    documents = URL(
        r'/outil/UWDM/ConsultationDocument/derniersReleves',
        r'/outil/UWDM/Recherche/rechercherAll',
        DocumentsPage)
    documents_plus = URL(r'/outil/UWDM/Recherche/afficherPlus', DocumentsPage)

    profile = URL(r'/outil/UWIP/Accueil/rafraichir', ProfilePage)

    deposit = URL(r'/outil/UWPL/CompteATerme/accesSynthese',
                  r'/outil/UWPL/DetailCompteATerme/accesDetail', DepositPage)

    __states__ = ('contracts', 'current_contract', 'parsed_contracts')

    IDENTIFIANT_ROUTING = 'CLI'

    def __init__(self, *args, **kwargs):
        super(LCLBrowser, self).__init__(*args, **kwargs)
        self.accounts_list = None
        self.current_contract = None
        self.contracts = []
        self.parsed_contracts = False
        self.owner_type = AccountOwnerType.PRIVATE

    def load_state(self, state):
        super(LCLBrowser, self).load_state(state)

        # lxml _ElementStringResult were put in the state, convert them to plain strs
        # TODO to remove at some point
        if self.contracts:
            self.contracts = [unicode(s) for s in self.contracts]
        if self.current_contract:
            self.current_contract = unicode(self.current_contract)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)

        if not self.password.isdigit():
            raise BrowserIncorrectPassword()

        # Since a while the virtual keyboard accepts only the first 6 digits of the password
        self.password = self.password[:6]

        # we force the browser to go to login page so it's work even
        # if the session expire
        # Must set the referer to avoid redirection to the home page
        self.login.go(headers={"Referer": "https://www.lcl.fr/"})

        if not self.page.login(self.username, self.password) or self.login.is_here():
            self.page.check_error()

        if not self.contracts and not self.parsed_contracts:
            # On the preRoutageLogin page we gather the list of available contracts for this account
            self.contracts = self.page.get_contracts_list()
            # If there is not multiple contracts then self.contracts will be empty
            if not self.contracts:
                self.page.select_contract()
            self.parsed_contracts = True

        self.accounts_list = None
        self.accounts.stay_or_go()

    @need_login
    def connexion_bourse(self):
        self.location('/outil/UWBO/AccesBourse/temporisationCar?codeTicker=TICKERBOURSECLI')
        if self.no_perm.is_here():
            return False
        next_page = self.page.get_next()
        if next_page:
            # go on a intermediate page to get a session cookie (jsessionid)
            self.location(next_page)
            # go to bourse page
            self.bourse.stay_or_go()
            return True

    def deconnexion_bourse(self):
        self.disc.stay_or_go()

    @need_login
    def go_life_insurance_website(self):
        self.assurancevie.stay_or_go()
        life_insurance_routage_url = self.page.get_routage_url()
        if life_insurance_routage_url:
            self.location(life_insurance_routage_url)
            self.av_list.go()

    @need_login
    def update_life_insurance_account(self, life_insurance):
        self.av_investments.go(life_insurance_id=life_insurance.id)
        return self.page.update_life_insurance_account(life_insurance)

    @need_login
    def go_back_from_life_insurance_website(self):
        self.avdetail.stay_or_go()
        self.page.come_back()

    def select_contract(self, id_contract):
        if self.current_contract and id_contract != self.current_contract:
            self.logger.debug('Changing contract to %s', id_contract)
            # when we go on bourse page, we can't change contract anymore... we have to logout.
            self.location('/outil/UAUT/Login/logout')
            # we already passed all checks on do_login so we consider it's ok.
            self.login.go().login(self.username, self.password)
            self.contracts_choice.go().select_contract(id_contract)

    def go_contract(f):
        @wraps(f)
        def wrapper(self, account, *args, **kwargs):
            self.select_contract(account._contract)
            return f(self, account, *args, **kwargs)
        return wrapper

    def check_accounts(self, account):
        return all(account.id != acc.id for acc in self.accounts_list)

    def update_accounts(self, account):
        if self.check_accounts(account):
            account._contract = self.current_contract
            self.accounts_list.append(account)

    def set_deposit_account_id(self, account):
        self.deposit.go()
        if self.no_perm.is_here():
            self.logger.warning('Deposits are unavailable.')
        else:
            form = self.page.get_form(id='mainform')
            form['INDEX'] = account._link_index
            form.submit()
            self.page.set_deposit_account_id(account)
        self.deposit.go()

    @need_login
    def get_accounts(self):
        # This is required in case the browser is left in the middle of add_recipient and the session expires.
        if self.login.is_here():
            return self.get_accounts_list()

        profile_name = self.get_profile_name()
        if ' ' in profile_name:
            owner_name = re.search(r' (.+)', profile_name).group(1).upper()
        else:
            owner_name = profile_name.upper()

        # retrieve life insurance accounts
        self.assurancevie.stay_or_go()
        if self.no_perm.is_here():
            self.logger.warning('Life insurances are unavailable.')
        else:
            # retrieve life insurances from popups
            for a in self.page.get_popup_life_insurance(name=owner_name):
                self.update_accounts(a)

            # retrieve life insurances from calie website
            calie_index = self.page.get_calie_life_insurances_first_index()
            if calie_index:
                form = self.page.get_form(id="formRedirectPart")
                form['INDEX'] = calie_index
                form.submit()
                # if only one calie insurance, request directly leads to details on CaliePage
                if self.calie_detail.is_here():
                    self.page.check_error()
                    a = Account()
                    a.url = self.url
                    self.page.fill_account(obj=a)
                    self.update_accounts(a)
                # if several calie insurances, request leads to CalieContractsPage
                elif self.calie_contracts.is_here():
                    for a in self.page.iter_calie_life_insurance():
                        if a.url:
                            self.location(a.url)
                            self.page.fill_account(obj=a)
                            self.update_accounts(a)
                        else:
                            self.logger.warning('%s has no url to parse detail to' % a)
                # get back to life insurances list page
                self.assurancevie.stay_or_go()

            # retrieve life insurances on special lcl life insurance website
            if self.page.is_website_life_insurance():
                self.go_life_insurance_website()
                for life_insurance in self.page.iter_life_insurance():
                    life_insurance = self.update_life_insurance_account(life_insurance)
                    self.update_accounts(life_insurance)
                self.go_back_from_life_insurance_website()

        # retrieve accounts on main page
        self.accounts.go()
        for a in self.page.get_accounts_list(name=owner_name):
            if not self.check_accounts(a):
                continue

            self.location('/outil/UWRI/Accueil/')
            if self.no_perm.is_here():
                self.logger.warning('RIB is unavailable.')
            elif self.page.has_iban_choice():
                self.rib.go(data={'compte': '%s/%s/%s' % (a.id[0:5], a.id[5:11], a.id[11:])})
                if self.rib.is_here():
                    iban = self.page.get_iban()
                    a.iban = iban if iban and a.id[11:] in iban else NotAvailable
            else:
                iban = self.page.check_iban_by_account(a.id)
                a.iban = iban if iban is not None else NotAvailable
            self.update_accounts(a)

        # retrieve loans accounts
        self.loans.stay_or_go()
        if self.no_perm.is_here():
            self.logger.warning('Loans are unavailable.')
        else:
            for a in self.page.get_list():
                self.update_accounts(a)

        # retrieve pro loans accounts
        self.loans_pro.stay_or_go()
        if self.no_perm.is_here():
            self.logger.warning('Loans are unavailable.')
        else:
            for a in self.page.get_list():
                self.update_accounts(a)

        if self.connexion_bourse():
            for a in self.page.get_list(name=owner_name):
                self.update_accounts(a)
            self.deconnexion_bourse()
            # Disconnecting from bourse portal before returning account list
            # to be sure that we are on the banque portal

        # retrieve deposit accounts
        self.deposit.stay_or_go()
        if self.no_perm.is_here():
            self.logger.warning('Deposits are unavailable.')
        else:
            for a in self.page.get_list(name=owner_name):
                # There is no id on the page listing the 'Compte à terme'
                # So a form must be submitted to access the id of the contract
                self.set_deposit_account_id(a)
                self.update_accounts(a)

    @need_login
    def get_accounts_list(self):
        if self.accounts_list is None:
            self.accounts_list = []

            if self.contracts and self.current_contract:
                for id_contract in self.contracts:
                    self.select_contract(id_contract)
                    self.get_accounts()
            else:
                self.get_accounts()

        self.accounts.go()

        deferred_cards = self.page.get_deferred_cards()

        # We got deferred card page link and we have to go through it to get details.
        for account_id, link in deferred_cards:
            parent_account = find_object(self.accounts_list, id=account_id)
            self.location(link)
            # Url to go to each account card is made of agence id, parent account id,
            # parent account key id and an index of the card (0,1,2,3,4...).
            # This index is not related to any information, it's just an incremental integer
            for card_position, a in enumerate(self.page.get_child_cards(parent_account)):
                a._card_position = card_position
                self.update_accounts(a)

        profile_name = self.get_profile_name()
        if ' ' in profile_name:
            owner_name = re.search(r' (.+)', profile_name).group(1).upper()
        else:
            owner_name = profile_name.upper()

        for account in self.accounts_list:
            account.owner_type = self.owner_type
            self.set_ownership(account, owner_name)

        return iter(self.accounts_list)

    def set_ownership(self, account, owner_name):
        if not account.ownership:
            if account.parent and account.parent.ownership:
                account.ownership = account.parent.ownership
            elif re.search(r'(m|mr|me|mme|mlle|mle|ml)\.? (.*)\bou (m|mr|me|mme|mlle|mle|ml)\b(.*)', account.label, re.IGNORECASE):
                account.ownership = AccountOwnership.CO_OWNER
            elif all(n in account.label for n in owner_name.split()):
                account.ownership = AccountOwnership.OWNER
            else:
                account.ownership = AccountOwnership.ATTORNEY

    def get_bourse_accounts_ids(self):
        bourse_accounts_ids = []
        for account in self.get_accounts_list():
            if 'bourse' in account.id:
                bourse_accounts_ids.append(account.id.split('bourse')[0])
        return bourse_accounts_ids

    @go_contract
    @need_login
    def get_history(self, account):
        if hasattr(account, '_market_link') and account._market_link:
            self.connexion_bourse()
            self.location(account._link_id, params={
                'nump': account._market_id,
            })
            self.page.get_fullhistory()
            for tr in self.page.iter_history():
                yield tr
            self.deconnexion_bourse()
        elif hasattr(account, '_link_id') and account._link_id:
            try:
                self.location(account._link_id)
            except ServerError:
                return
            if self.login.is_here():
                # Website crashed and we are disconnected.
                raise BrowserUnavailable()
            for tr in self.page.get_operations():
                yield tr

        elif account.type == Account.TYPE_CARD:
            for tr in self.get_cb_operations(account=account, month=1):
                yield tr

        elif account.type == Account.TYPE_LIFE_INSURANCE:
            if not account._external_website:
                self.logger.warning('This account is limited, there is no available history.')
                return

            if account._is_calie_account:
                # TODO build parsing of history page, all-you-can-eat js in it
                # follow 'account._history_url' for that
                raise NotImplementedError()
            else:
                self.assurancevie.stay_or_go()
                self.go_life_insurance_website()
                assert self.av_list.is_here(), 'Something went wrong during iter life insurance history'
                # Need to be on account details page to do history request
                self.av_investments.go(life_insurance_id=account.id)
                self.av_history.go()
                for tr in self.page.iter_history():
                    yield tr
                self.go_back_from_life_insurance_website()

    @need_login
    def get_coming(self, account):
        if account.type == Account.TYPE_CARD:
            for tr in self.get_cb_operations(account=account, month=0):
                yield tr

    # %todo check this decorator : @go_contract
    @need_login
    def get_cb_operations(self, account, month=0):
        """
        Get CB operations.

        * month=0 : current operations (non debited)
        * month=1 : previous month operations (debited)
        """

        # Separation of bank account id and bank account key
        # example : 123456A
        regex = r'([0-9]{6})([A-Z]{1})'
        account_id_regex = re.match(regex, account.parent._compte)

        args = {
            'AGENCE': account.parent._agence,
            'COMPTE': account_id_regex.group(1),
            'CLE': account_id_regex.group(2),
            'NUMEROCARTE': account._card_position,
            'MOIS': month,
        }

        # We must go to '_cards_list' url first before transaction_link, otherwise, the website
        # will show same transactions for all account, despite different values in 'args'.
        assert 'MOIS=' in account._cards_list, 'Missing "MOIS=" in url'
        init_url = account._cards_list.replace('MOIS=0', 'MOIS=%s' % month)
        self.location(init_url)
        self.location(account._transactions_link, params=args)

        if month == 1:
            summary = self.page.get_card_summary()
            if summary:
                yield summary

        for tr in self.page.iter_transactions():
            # Strange behavior, but sometimes, rdate > date.
            # We skip it to avoid duplicate transactions.
            if tr.date >= tr.rdate:
                yield tr

    @go_contract
    @need_login
    def get_investment(self, account):
        if account.type == Account.TYPE_LIFE_INSURANCE:
            if not account._external_website:
                self.logger.warning('This account is limited, there is no available investment.')
                return

            self.assurancevie.stay_or_go()
            if account._is_calie_account:
                calie_details = self.open(account.url)
                for inv in calie_details.page.iter_investment():
                    yield inv
            else:
                self.go_life_insurance_website()
                assert self.av_list.is_here(), 'Something went wrong during iter life insurance investments'
                self.av_investments.go(life_insurance_id=account.id)
                for inv in self.page.iter_investment():
                    yield inv
                self.go_back_from_life_insurance_website()

        elif hasattr(account, '_market_link') and account._market_link:
            self.connexion_bourse()
            for inv in self.location(account._market_link).page.iter_investment():
                yield inv
            self.deconnexion_bourse()
        elif account.id in self.get_bourse_accounts_ids():
            yield create_french_liquidity(account.balance)

    def locate_browser(self, state):
        if state['url'] == 'https://particuliers.secure.lcl.fr/outil/UWBE/Creation/creationConfirmation':
            self.logged = True
        else:
            super(LCLBrowser, self).locate_browser(state)

    @need_login
    def send_code(self, recipient, **params):
        res = self.open('/outil/UWBE/Otp/validationCodeOtp?codeOtp=%s' % params['code'])
        if res.text == 'false':
            raise AddRecipientBankError(message='Mauvais code sms.')
        self.recip_recap.go().check_values(recipient.iban, recipient.label)
        return self.get_recipient_object(recipient.iban, recipient.label)

    @need_login
    def get_recipient_object(self, iban, label):
        r = Recipient()
        r.iban = iban
        r.id = iban
        r.label = label
        r.category = u'Externe'
        r.enabled_at = datetime.now().replace(microsecond=0) + timedelta(days=5)
        r.currency = u'EUR'
        r.bank_name = NotAvailable
        return r

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            return self.send_code(recipient, **params)

        if recipient.iban[:2] not in ('FR', 'MC'):
            raise AddRecipientBankError(message=u"LCL n'accepte que les iban commençant par MC ou FR.")

        for _ in range(2):
            self.add_recip.go()
            if self.add_recip.is_here():
                break

        if self.no_perm.is_here() and self.page.get_error_msg():
            raise AddRecipientBankError(message=self.page.get_error_msg())

        assert self.add_recip.is_here(), 'Navigation failed: not on add_recip'
        self.page.validate(recipient.iban, recipient.label)

        assert self.recip_confirm.is_here(), 'Navigation failed: not on recip_confirm'
        self.page.check_values(recipient.iban, recipient.label)

        # Send sms to user.
        self.open('/outil/UWBE/Otp/envoiCodeOtp?telChoisi=MOBILE')
        raise AddRecipientStep(self.get_recipient_object(recipient.iban, recipient.label), Value('code', label='Saisissez le code.'))

    @go_contract
    @need_login
    def iter_recipients(self, origin_account):
        if origin_account._transfer_id is None:
            return
        self.transfer_page.go()
        if self.no_perm.is_here() or not self.page.can_transfer(origin_account._transfer_id):
            return
        self.page.choose_origin(origin_account._transfer_id)
        for recipient in self.page.iter_recipients(account_transfer_id=origin_account._transfer_id):
            yield recipient

    @go_contract
    @need_login
    def init_transfer(self, account, recipient, amount, reason=None, exec_date=None):
        self.transfer_page.go()
        self.page.choose_origin(account._transfer_id)
        self.page.choose_recip(recipient)

        if exec_date == date.today():
            self.page.transfer(amount, reason)
        else:
            self.page.deferred_transfer(amount, reason, exec_date)
        return self.page.handle_response(account, recipient)

    @need_login
    def execute_transfer(self, transfer):
        self.page.confirm()
        self.page.check_error()
        return transfer

    @need_login
    def get_advisor(self):
        return iter([self.accounts.stay_or_go().get_advisor()])

    @need_login
    def iter_subscriptions(self):
        yield self.client.go().get_item()

    @need_login
    def iter_documents(self, subscription):
        documents = []
        self.documents.go()
        self.documents_plus.go()
        self.page.do_search_request()
        for document in self.page.get_list():
            documents.append(document)
        return documents

    def get_profile_name(self):
        self.accounts.stay_or_go()
        return self.page.get_name()

    @need_login
    def get_profile(self):
        name = self.get_profile_name()
        # The self.get_profile_name() already does a
        # self.accounts.stay_or_go()
        self.profile.go(method="POST")
        profile = self.page.get_profile(name=name)
        return profile


class LCLProBrowser(LCLBrowser):
    BASEURL = 'https://professionnels.secure.lcl.fr'

    # We need to add this on the login form
    IDENTIFIANT_ROUTING = 'CLA'

    def __init__(self, *args, **kwargs):
        super(LCLProBrowser, self).__init__(*args, **kwargs)
        self.session.cookies.set("lclgen", "professionnels", domain=urlsplit(self.BASEURL).hostname)
        self.owner_type = AccountOwnerType.ORGANIZATION


class ELCLBrowser(LCLBrowser):
    BASEURL = 'https://e.secure.lcl.fr'

    IDENTIFIANT_ROUTING = 'ELCL'

    def __init__(self, *args, **kwargs):
        super(ELCLBrowser, self).__init__(*args, **kwargs)

        self.session.cookies.set('lclgen', 'ecl', domain=urlsplit(self.BASEURL).hostname)

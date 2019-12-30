# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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

import time

from datetime import datetime
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from weboob.browser import URL, need_login
from weboob.browser.browsers import TwoFactorBrowser
from weboob.capabilities.bill import Document, DocumentTypes
from weboob.exceptions import (
    BrowserIncorrectPassword, ActionNeeded, BrowserUnavailable,
    AppValidation, BrowserQuestion, AppValidationError, AppValidationCancelled,
    AppValidationExpired, AuthMethodNotImplemented,
)
from weboob.capabilities.bank import Account, TransferBankError, AddRecipientStep, TransactionType, AccountOwnerType
from weboob.capabilities.base import find_object, NotAvailable
from weboob.browser.exceptions import BrowserHTTPNotFound, ClientError
from weboob.capabilities.profile import ProfileMissing
from weboob.tools.value import Value, ValueBool
from weboob.tools.decorators import retry

from .pages.accounts_list import (
    AccountsMainPage, AccountDetailsPage, AccountsPage, LoansPage, HistoryPage,
    CardHistoryPage, PeaLiquidityPage,
    AdvisorPage, HTMLProfilePage, CreditPage, CreditHistoryPage, OldHistoryPage,
    MarketPage, LifeInsurance, LifeInsuranceHistory, LifeInsuranceInvest, LifeInsuranceInvest2,
    UnavailableServicePage, LoanDetailsPage, TemporaryBrowserUnavailable,
)
from .pages.transfer import AddRecipientPage, SignRecipientPage, TransferJson, SignTransferPage
from .pages.login import MainPage, LoginPage, BadLoginPage, ReinitPasswordPage, ActionNeededPage, ErrorPage
from .pages.subscription import BankStatementPage, RibPdfPage


__all__ = ['SocieteGenerale']


class SocieteGenerale(TwoFactorBrowser):
    HAS_REGULAR_LOGIN = True

    BASEURL = 'https://particuliers.societegenerale.fr'
    # XXX STATE_DURATION was 5 minutes for transfers purposes...

    # Bank
    accounts_main_page = URL(r'/restitution/cns_listeprestation.html',
                             r'/com/icd-web/cbo/index.html', AccountsMainPage)
    account_details_page = URL(r'/restitution/cns_detailPrestation.html', AccountDetailsPage)
    accounts = URL(r'/icd/cbo/data/liste-prestations-authsec.json\?n10_avecMontant=1', AccountsPage)
    history = URL(r'/icd/cbo/data/liste-operations-authsec.json', HistoryPage)
    loans = URL(r'/abm/restit/listeRestitutionPretsNET.json\?a100_isPretConso=(?P<conso>\w+)', LoansPage)
    loan_details_page = URL(r'icd/cbo/data/recapitulatif-prestation-authsec.json', LoanDetailsPage)

    card_history = URL(r'/restitution/cns_listeReleveCarteDd.xml', CardHistoryPage)
    credit = URL(r'/restitution/cns_detailAVPAT.html', CreditPage)
    credit_history = URL(r'/restitution/cns_listeEcrCav.xml', CreditHistoryPage)
    old_hist_page = URL(r'/restitution/cns_detailPep.html',
                        r'/restitution/cns_listeEcrPep.html',
                        r'/restitution/cns_detailAlterna.html',
                        r'/restitution/cns_listeEncoursAlterna.html', OldHistoryPage)

    # Recipient
    add_recipient = URL(r'/personnalisation/per_cptBen_ajouterFrBic.html',
                        r'/lgn/url.html', AddRecipientPage)
    json_recipient = URL(r'/sec/getsigninfo.json',
                         r'/sec/csa/send.json',
                         r'/sec/oob_sendoob.json',
                         r'/sec/oob_polling.json', SignRecipientPage)
    # Transfer
    json_transfer = URL(r'/icd/vupri/data/vupri-liste-comptes.json\?an200_isBack=false',
                        r'/icd/vupri/data/vupri-check.json',
                        r'/lgn/url.html', TransferJson)
    sign_transfer = URL(r'/icd/vupri/data/vupri-generate-token.json', SignTransferPage)
    confirm_transfer = URL(r'/icd/vupri/data/vupri-save.json', TransferJson)

    # Wealth
    market = URL(r'/brs/cct/comti20.html', MarketPage)
    pea_liquidity = URL(r'/restitution/cns_detailPea.html', PeaLiquidityPage)
    life_insurance = URL(r'/asv/asvcns10.html',
                         r'/asv/AVI/asvcns10a.html',
                         r'/brs/fisc/fisca10a.html', LifeInsurance)
    life_insurance_invest = URL(r'/asv/AVI/asvcns20a.html', LifeInsuranceInvest)
    life_insurance_invest_2 = URL(r'/asv/PRV/asvcns10priv.html', LifeInsuranceInvest2)
    life_insurance_history = URL(r'/asv/AVI/asvcns2(?P<n>[0-9])c.html', LifeInsuranceHistory)

    # Profile
    advisor = URL(r'/icd/pon/data/get-contacts.xml', AdvisorPage)
    html_profile_page = URL(r'/com/dcr-web/dcr/dcr-coordonnees.html', HTMLProfilePage)

    # Document
    bank_statement = URL(r'/restitution/rce_derniers_releves.html', BankStatementPage)
    bank_statement_search = URL(r'/restitution/rce_recherche.html\?noRedirect=1',
                                r'/restitution/rce_recherche_resultat.html', BankStatementPage)
    rib_pdf_page = URL(r'/com/icd-web/cbo/pdf/rib-authsec.pdf', RibPdfPage)

    bad_login = URL(r'/acces/authlgn.html', r'/error403.html', BadLoginPage)
    reinit = URL(r'/acces/changecodeobligatoire.html',
                 r'/swm/swm-changemdpobligatoire.html', ReinitPasswordPage)
    action_needed = URL(r'/com/icd-web/forms/cct-index.html',
                        r'/com/icd-web/gdpr/gdpr-recueil-consentements.html',
                        r'/com/icd-web/forms/kyc-index.html',
                        ActionNeededPage)
    unavailable_service_page = URL(r'/com/service-indisponible.html',
                                   r'.*/Technical-pages/503-error-page/unavailable.html',
                                   r'.*/Technical-pages/service-indisponible/service-indisponible.html',
                                   UnavailableServicePage)
    error = URL(r'https://static.societegenerale.fr/pri/erreur.html',
                r'https://.*/pri/erreur.html', ErrorPage)
    login = URL(r'https://particuliers.societegenerale.fr//sec/vk/',  # yes, it works only with double slash
                r'/sec/oob_sendooba.json',
                r'/sec/oob_pollingooba.json',
                r'/sec/oob_auth.json',
                r'/sec/csa/check.json', LoginPage)
    main_page = URL(r'https://particuliers.societegenerale.fr', MainPage)

    context = None
    dup = None
    id_transaction = None
    polling_transaction = None
    polling_duration = 300  # default to 5 minutes

    __states__ = ('context', 'dup', 'id_transaction', 'polling_transaction',)

    def transfer_condition(self, state):
        return state.get('dup') is not None and state.get('context') is not None

    def locate_browser(self, state):
        if self.transfer_condition(state):
            self.location('/com/icd-web/cbo/index.html')
        elif all(url not in state['url'] for url in self.login.urls):
            super(SocieteGenerale, self).locate_browser(state)

    def check_password(self):
        if not self.password.isdigit() or len(self.password) not in (6, 7):
            raise BrowserIncorrectPassword()
        if not self.username.isdigit() or len(self.username) < 8:
            raise BrowserIncorrectPassword()

    def check_login_reason(self):
        reason = self.page.get_reason()

        if reason == 'echec_authent':
            raise BrowserIncorrectPassword()
        elif reason in ('acces_bloq', 'acces_susp', 'pas_acces_bad', ):
            raise ActionNeeded()
        elif reason == 'err_tech':
            # there is message "Service momentanément indisponible. Veuillez réessayer."
            # in SG website in that case ...
            raise BrowserUnavailable()

    def check_auth_method(self):
        auth_method = self.page.get_auth_method()

        if not auth_method:
            self.logger.warning('No auth method available !')
            raise ActionNeeded(
                'Veuillez ajouter un numéro de téléphone sur votre banque et/ou activer votre Pass Sécurité'
            )

        if auth_method['unavailability_reason'] == "ts_non_enrole":
            raise ActionNeeded(
                'Veuillez ajouter un numéro de téléphone sur votre banque'
            )

        elif auth_method['unavailability_reason']:
            assert False, 'Unknown unavailability reason "%s" found' % auth_method['unavailability_reason']

        if auth_method['type_proc'].lower() == 'auth_oob':
            self.location('/sec/oob_sendooba.json', method='POST', headers={'Content-Type': 'application/x-www-form-urlencoded'},)

            donnees = self.page.doc['donnees']
            self.polling_transaction = donnees['id-transaction']

            if donnees.get('expiration_date_hh') and donnees.get('expiration_date_mm'):
                now = datetime.now()
                expiration_date = now.replace(
                    hour=int(donnees['expiration_date_hh']),
                    minute=int(donnees['expiration_date_mm'])
                )
                self.polling_duration = int((expiration_date - now).total_seconds())

            message = "Veuillez valider l'opération dans votre application"
            terminal_name = auth_method['terminal'][0]['nom']
            if terminal_name:
                message += " sur " + terminal_name

            raise AppValidation(message)

        elif auth_method['type_proc'].lower() == 'auth_csa':
            if auth_method['mode'] == "SMS":
                self.location(
                    '/sec/csa/send.json',
                    data={'csa_op': "auth",}
                )
                raise BrowserQuestion(
                    Value(
                        'code',
                        label='Entrez le Code Sécurité reçu par SMS sur le numéro ' + auth_method['ts']
                    )
                )

            self.logger.warning('Unknown CSA method "%s" found', auth_method['mod'])

        else:
            self.logger.warning('Unknown sign method "%s" found', auth_method['sign_proc'])

        raise AuthMethodNotImplemented()

    def init_login(self):
        self.check_password()

        self.main_page.go()
        try:
            self.page.login(self.username[:8], self.password)
        except BrowserHTTPNotFound:
            raise BrowserIncorrectPassword()

        assert self.login.is_here(), "An error has occured, we should be on login page."

        self.check_login_reason()

        if self.page.has_twofactor():
            self.check_interactive()
            self.check_auth_method()

    def check_polling_errors(self, status):
        if status == "rejected":
            raise AppValidationCancelled(
                "L'opération dans votre application a été annulée"
            )

        if status == "aborted":
            raise AppValidationExpired(
                "L'opération dans votre application a expirée"
            )

        if status != "available":
            raise AppValidationError()

    def handle_polling(self):
        assert self.polling_transaction, "polling_transaction is mandatory !"

        data = {'n10_id_transaction': self.polling_transaction}
        timeout = time.time() + self.polling_duration
        while time.time() < timeout:
            self.location('/sec/oob_pollingooba.json', data=data)

            status = self.page.doc['donnees']['transaction_status']
            if status != "in_progress":
                break

            time.sleep(3)
        else:
            status = "aborted"

        self.check_polling_errors(status)

        data.update({'oob_op': "auth",})
        self.location('/sec/oob_auth.json', data=data)

        if self.page.doc.get('commun', {}).get('statut').lower() == "nok":
            raise BrowserUnavailable()

        self.polling_transaction = None

    def handle_sms(self):
        if len(self.code) != 6:
            raise BrowserIncorrectPassword(
                'Le Code Sécurité doit avoir une taille de 6 caractères'
            )

        data = {
            'code': self.code,
            'csa_op': "auth",
        }
        self.location('/sec/csa/check.json', data=data)

        if self.page.doc.get('commun', {}).get('statut').lower() == "nok":
            raise BrowserIncorrectPassword('Le Code Sécurité est invalide')

    def iter_cards(self, account):
        for el in account._cards:
            if el['carteDebitDiffere']:
                card = Account()
                card.id = card.number = el['numeroCompteFormate'].replace(' ', '')
                card.label = el['labelToDisplay']
                card.balance = Decimal('0')
                card.coming = Decimal(str(el['montantProchaineEcheance']))
                card.type = Account.TYPE_CARD
                card.currency = account.currency
                card._internal_id = el['idTechnique']
                card._prestation_id = el['id']
                card.owner_type = AccountOwnerType.PRIVATE
                yield card

    @need_login
    def get_accounts_list(self):
        self.accounts_main_page.go()
        self.page.is_accounts()

        if self.page.is_old_website():
            # go on new_website
            self.location(self.absurl('/com/icd-web/cbo/index.html'))

        # get account iban on transfer page
        account_ibans = {}
        try:
            self.json_transfer.go()
        except (TransferBankError, ClientError, BrowserUnavailable):
            # some user can't access this page
            pass
        else:
            account_ibans = self.page.get_account_ibans_dict()

        go = retry(TemporaryBrowserUnavailable)(self.accounts.go)
        go()

        if not self.page.is_new_website_available():
            # return in old pages to get accounts
            self.accounts_main_page.go(params={'NoRedirect': True})
            for acc in self.page.iter_accounts():
                yield acc
            return

        accounts = {}
        for account in self.page.iter_accounts():
            account._parent_id = None
            for card in self.iter_cards(account):
                card.parent = account
                card.ownership = account.ownership
                card.owner_type = AccountOwnerType.PRIVATE
                yield card

            account.owner_type = AccountOwnerType.PRIVATE

            if account._prestation_id in account_ibans:
                account.iban = account_ibans[account._prestation_id]

            if account.type in (account.TYPE_LOAN, account.TYPE_CONSUMER_CREDIT, ):
                self.loans.stay_or_go(conso=(account._loan_type == 'PR_CONSO'))
                account = self.page.get_loan_account(account)

            if account.type == account.TYPE_REVOLVING_CREDIT:
                self.loans.stay_or_go(conso=(account._loan_type == 'PR_CONSO'))
                account = self.page.get_revolving_account(account)
                self.loan_details_page.go(params={'b64e200_prestationIdTechnique': account._internal_id})
                self.page.set_loan_details(account)

            accounts[account.id] = account

        # Adding parent account to LOAN account
        for account_id, account in accounts.items():
            if account._parent_id:
                account.parent = accounts.get(account._parent_id, NotAvailable)

            yield account

    def next_page_retry(self, condition):
        next_page = self.page.hist_pagination(condition)
        if next_page:
            location = retry(TemporaryBrowserUnavailable)(self.location)
            location(next_page)
            return True
        return False

    @need_login
    def iter_history(self, account):
        if account.type in (account.TYPE_LOAN, account.TYPE_MARKET, account.TYPE_CONSUMER_CREDIT, ):
            return

        if account.type == Account.TYPE_PEA and not ('Espèces' in account.label or 'ESPECE' in account.label):
            return

        if not account._internal_id:
            raise BrowserUnavailable()

        # get history for account on old website
        # request to get json is not available yet, old request to get html response
        if any((
                account.type in (account.TYPE_LIFE_INSURANCE, account.TYPE_PERP),
                account.type == account.TYPE_REVOLVING_CREDIT and account._loan_type != 'PR_CONSO',
                account.type in (account.TYPE_REVOLVING_CREDIT, account.TYPE_SAVINGS) and not account._is_json_histo
        )):
            go = retry(TemporaryBrowserUnavailable)(self.account_details_page.go)
            go(params={'idprest': account._prestation_id})

            history_url = self.page.get_history_url()

            # history_url return NotAvailable when history page doesn't exist
            # it return None when we don't know if history page exist
            if history_url is None:
                error_msg = self.page.get_error_msg()
                assert error_msg, 'There should have error or history url'
                raise BrowserUnavailable(error_msg)
            elif history_url:
                self.location(self.absurl(history_url))

            for tr in self.page.iter_history():
                yield tr
            return

        if account.type == account.TYPE_CARD:
            go = retry(TemporaryBrowserUnavailable)(self.history.go)
            go(params={'b64e200_prestationIdTechnique': account.parent._internal_id})

            next_page = True
            while next_page:
                for summary_card_tr in self.page.iter_card_transactions(card_number=account.number):
                    yield summary_card_tr

                    for card_tr in summary_card_tr._card_transactions:
                        card_tr.date = summary_card_tr.date
                        # We use the Raw pattern to set the rdate automatically, but that make
                        # the transaction type to "CARD", so we have to correct it in the browser.
                        card_tr.type = TransactionType.DEFERRED_CARD
                        yield card_tr
                next_page = self.next_page_retry('history')
            return

        go = retry(TemporaryBrowserUnavailable)(self.history.go)
        go(params={'b64e200_prestationIdTechnique': account._internal_id})

        next_page = True
        while next_page:
            for transaction in self.page.iter_history():
                yield transaction
            next_page = self.next_page_retry('history')

    @need_login
    def iter_coming(self, account):
        if account.type in (account.TYPE_LOAN, account.TYPE_MARKET, account.TYPE_PEA,
                            account.TYPE_LIFE_INSURANCE, account.TYPE_REVOLVING_CREDIT,
                            account.TYPE_CONSUMER_CREDIT, Account.TYPE_PERP, ):
            return

        if not account._internal_id:
            raise BrowserUnavailable()

        if account.type == account.TYPE_SAVINGS and not account._is_json_histo:
            # Waiting for account with transactions
            return

        internal_id = account._internal_id
        if account.type == account.TYPE_CARD:
            internal_id = account.parent._internal_id

        go = retry(TemporaryBrowserUnavailable)(self.history.go)
        go(params={'b64e200_prestationIdTechnique': internal_id})

        if account.type == account.TYPE_CARD:
            next_page = True
            while next_page:
                for transaction in self.page.iter_future_transactions(acc_prestation_id=account._prestation_id):
                    # coming transactions on this page are not included in coming balance
                    # use it only to retrive deferred card coming transactions
                    if transaction._card_coming:
                        for card_coming in transaction._card_coming:
                            card_coming.date = transaction.date
                            # We use the Raw pattern to set the rdate automatically, but that makes
                            # the transaction type to "CARD", so we have to correct it in the browser.
                            card_coming.type = TransactionType.DEFERRED_CARD
                            yield card_coming
                next_page = self.next_page_retry('future')
            return

        next_page = True
        while next_page:
            for intraday_tr in self.page.iter_intraday_comings():
                yield intraday_tr
            next_page = self.next_page_retry('intraday')

    @need_login
    def iter_investment(self, account):
        if account.type not in (Account.TYPE_MARKET, Account.TYPE_LIFE_INSURANCE,
                                Account.TYPE_PEA, Account.TYPE_PERP, ):
            self.logger.debug('This account is not supported')
            return

        # request to get json is not available yet, old request to get html response
        self.account_details_page.go(params={'idprest': account._prestation_id})

        if account.type in (Account.TYPE_PEA, Account.TYPE_MARKET):
            for invest in self.page.iter_investments(account=account):
                yield invest

        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_PERP, ):
            if self.page.has_link():
                self.life_insurance_invest.go()

            for invest in self.page.iter_investment():
                yield invest

    @need_login
    def iter_recipients(self, account):
        try:
            self.json_transfer.go()
        except TransferBankError:
            return []
        if not self.page.is_able_to_transfer(account):
            return []
        return self.page.iter_recipients(account_id=account.id)

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.json_transfer.go()

        first_transfer_date = self.page.get_first_available_transfer_date()
        if transfer.exec_date and transfer.exec_date < first_transfer_date:
            transfer.exec_date = first_transfer_date

        self.page.init_transfer(account, recipient, transfer)
        return self.page.handle_response(recipient)

    @need_login
    def execute_transfer(self, transfer):
        assert transfer.id, 'Transfer token is missing'
        data = {
            'b64e200_idVirement': transfer.id
        }
        # get token and virtual keyboard
        self.sign_transfer.go(params=data)

        data.update(self.page.get_confirm_transfer_data(self.password))
        # execute transfer
        headers = {'Referer': self.absurl('/com/icd-web/vupri/virement.html')}
        self.confirm_transfer.go(data=data, headers=headers)

        assert self.page.is_transfer_validated(), 'Something went wrong, transfer is not executed'
        return transfer

    def end_sms_recipient(self, recipient, **params):
        """End adding recipient with OTP SMS authentication"""
        data = [
            ('context', [self.context, self.context]),
            ('dup', self.dup),
            ('code', params['code']),
            ('csa_op', 'sign')
        ]
        # needed to confirm recipient validation
        add_recipient_url = self.absurl('/lgn/url.html', base=True)
        self.location(add_recipient_url, data=data, headers={'Referer': add_recipient_url})
        return self.page.get_recipient_object(recipient)

    def end_oob_recipient(self, recipient, **params):
        """End adding recipient with 'pass sécurité' authentication"""
        r = self.open(
            self.absurl('/sec/oob_polling.json'),
            data={'n10_id_transaction': self.id_transaction}
        )
        assert self.id_transaction, "Transaction id is missing, can't sign new recipient."
        r.page.check_recipient_status()

        data = [
            ('context', self.context),
            ('b64_jeton_transaction', self.context),
            ('dup', self.dup),
            ('n10_id_transaction', self.id_transaction),
            ('oob_op', 'sign')
        ]
        # needed to confirm recipient validation
        add_recipient_url = self.absurl('/lgn/url.html', base=True)
        self.location(add_recipient_url, data=data, headers={'Referer': add_recipient_url})
        return self.page.get_recipient_object(recipient)

    def send_sms_to_user(self, recipient):
        """Add recipient with OTP SMS authentication"""
        data = {}
        data['csa_op'] = 'sign'
        data['context'] = self.context
        self.open(self.absurl('/sec/csa/send.json'), data=data)
        raise AddRecipientStep(recipient, Value('code', label='Cette opération doit être validée par un Code Sécurité.'))

    def send_notif_to_user(self, recipient):
        """Add recipient with 'pass sécurité' authentication"""
        data = {}
        data['b64_jeton_transaction'] = self.context
        r = self.open(self.absurl('/sec/oob_sendoob.json'), data=data)
        self.id_transaction = r.page.get_transaction_id()
        raise AddRecipientStep(recipient, ValueBool('pass', label='Valider cette opération sur votre applicaton société générale'))

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            return self.end_sms_recipient(recipient, **params)
        if 'pass' in params:
            return self.end_oob_recipient(recipient, **params)

        self.add_recipient.go()
        if self.main_page.is_here():
            self.page.handle_error()
            assert False, 'Should not be on this page.'

        self.page.post_iban(recipient)
        self.page.post_label(recipient)

        recipient = self.page.get_recipient_object(recipient, get_info=True)
        self.page.update_browser_recipient_state()
        data = self.page.get_signinfo_data()

        r = self.open(self.absurl('/sec/getsigninfo.json'), data=data)
        sign_method = r.page.get_sign_method()

        # WARNING: this send validation request to user
        if sign_method == 'CSA':
            return self.send_sms_to_user(recipient)
        elif sign_method == 'OOB':
            return self.send_notif_to_user(recipient)
        assert False, 'Sign process unknown: %s' % sign_method

    @need_login
    def get_advisor(self):
        return self.advisor.go().get_advisor()

    @need_login
    def get_profile(self):
        self.html_profile_page.go()
        return self.page.get_profile()

    @need_login
    def iter_subscription(self):
        self.accounts_main_page.go()
        try:
            profile = self.get_profile()
            subscriber = profile.name
        except (ProfileMissing, BrowserUnavailable):
            subscriber = NotAvailable

        self.accounts.go()
        subscriptions_list = list(self.page.iter_subscription(subscriber=subscriber))

        self.bank_statement_search.go()
        searchable_subscription_list = list(self.page.iter_searchable_subscription())
        for sub in subscriptions_list:
            found_sub = find_object(searchable_subscription_list, id=sub.id)
            if found_sub:
                # we need it to get bank statement, but not all subscription have it
                sub._rad_button_id = found_sub._rad_button_id
            else:
                # even without bank statement we still can get RIB document, so we yield subscription anyway
                sub._rad_button_id = NotAvailable
            yield sub

    def _fetch_rib_document(self, subscription):
        d = Document()
        d.id = subscription.id + '_RIB'
        d.url = self.rib_pdf_page.build(params={'b64e200_prestationIdTechnique': subscription._internal_id})
        d.type = DocumentTypes.RIB
        d.format = 'pdf'
        d.label = 'RIB'
        return d

    def _iter_statements(self, subscription):
        # we need _rad_button_id for post_form function
        # if not present it means this subscription doesn't have any bank statement
        if subscription._rad_button_id is NotAvailable:
            return

        # 5 years since it goes with a 2 months step
        security_limit = 30
        end_date = datetime.today()
        i = 0
        while i < security_limit:
            self.bank_statement_search.go()
            self.page.post_form(subscription, end_date)

            # No more documents
            if self.page.has_error_msg():
                break

            for d in self.page.iter_documents(subscription):
                yield d

            # 3 months step because the documents list is inclusive
            # from the 08 to the 06, the 06 statement is included
            end_date = end_date - relativedelta(months=+3)
            i += 1

    @need_login
    def iter_documents(self, subscription):
        yield self._fetch_rib_document(subscription)
        for doc in self._iter_statements(subscription):
            yield doc

    @need_login
    def iter_documents_by_types(self, subscription, accepted_types):
        if DocumentTypes.RIB in accepted_types:
            yield self._fetch_rib_document(subscription)

        if DocumentTypes.STATEMENT not in accepted_types:
            return

        for doc in self._iter_statements(subscription):
            yield doc

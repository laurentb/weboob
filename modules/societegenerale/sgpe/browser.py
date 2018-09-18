# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

import re
from datetime import date

from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import (
    AccountNotFound, RecipientNotFound, AddRecipientStep, AddRecipientBankError,
    Recipient, TransferBankError,
)
from weboob.tools.value import Value

from .pages import (
    LoginPage, CardsPage, CardHistoryPage, IncorrectLoginPage,
    ProfileProPage, ProfileEntPage, ChangePassPage, SubscriptionPage,
)
from .json_pages import AccountsJsonPage, BalancesJsonPage, HistoryJsonPage, BankStatementPage
from .transfer_pages import (
    EasyTransferPage, RecipientsJsonPage, TransferPage, SignTransferPage, TransferDatesPage,
    AddRecipientPage, AddRecipientStepPage, ConfirmRecipientPage,
)


__all__ = ['SGProfessionalBrowser', 'SGEnterpriseBrowser']


class SGPEBrowser(LoginBrowser):
    login = URL('$', LoginPage)
    cards = URL('/Pgn/.+PageID=Cartes&.+', CardsPage)
    cards_history = URL('/Pgn/.+PageID=ReleveCarte&.+', CardHistoryPage)
    change_pass = URL('/gao/changer-code-secret-expire-saisie.html',
                      '/gao/changer-code-secret-inscr-saisie.html',
                      '/gao/inscrire-utilisateur-saisie.html',
                      '/gao/changer-code-secret-reattr-saisie.html',
                      '/gae/afficherInscriptionUtilisateur.html',
                      '/gae/afficherChangementCodeSecretExpire.html',
                      ChangePassPage)

    def check_logged_status(self):
        if not self.page or self.login.is_here():
            raise BrowserIncorrectPassword()

        error = self.page.get_error()
        if error:
            raise BrowserIncorrectPassword(error)

    def do_login(self):
        if not self.password.isdigit():
            raise BrowserIncorrectPassword('Password must be 6 digits long.')

        self.login.stay_or_go()
        if self.page.logged:
            return

        self.session.cookies.set('PILOTE_OOBA', 'true')
        try:
            self.page.login(self.username, self.password)
        except ClientError:
            raise BrowserIncorrectPassword()

        # force page change
        if not self.accounts.is_here():
            self.go_accounts()
        self.check_logged_status()

    def card_history(self, account, coming):
        page = 1
        while page:
            self.location('/Pgn/NavigationServlet?PageID=ReleveCarte&MenuID=%sOPF&Classeur=1&Rib=%s&Carte=%s&Date=%s&PageDetail=%s&Devise=%s' % \
                            (self.MENUID, account.id, coming['carte'], coming['date'], page, account.currency))
            for transaction in self.page.iter_transactions(date=coming['date']):
                yield transaction
            if self.page.has_next():
                page += 1
            else:
                page = False

    @need_login
    def get_cb_operations(self, account):
        self.location('/Pgn/NavigationServlet?PageID=Cartes&MenuID=%sOPF&Classeur=1&NumeroPage=1&Rib=%s&Devise=%s' % (self.MENUID, account.id, account.currency))
        for coming in self.page.get_coming_list():
            if coming['date'] == 'Non definie':
                # this is a very recent transaction and we don't know his date yet
                continue
            for tr in self.card_history(account, coming):
                yield tr

    def iter_investment(self, account):
        raise NotImplementedError()

    @need_login
    def get_profile(self):
        return self.profile.stay_or_go().get_profile()


class SGEnterpriseBrowser(SGPEBrowser):
    BASEURL = 'https://entreprises.secure.societegenerale.fr'
    LOGIN_FORM = 'auth'
    MENUID = 'BANREL'
    CERTHASH = '2231d5ddb97d2950d5e6fc4d986c23be4cd231c31ad530942343a8fdcc44bb99'

    accounts = URL('/icd/syd-front/data/syd-comptes-accederDepuisMenu.json', AccountsJsonPage)
    balances = URL('/icd/syd-front/data/syd-comptes-chargerSoldes.json', BalancesJsonPage)
    history = URL('/icd/syd-front/data/syd-comptes-chargerReleve.json',
                  '/icd/syd-front/data/syd-intraday-chargerDetail.json', HistoryJsonPage)
    history_next = URL('/icd/syd-front/data/syd-comptes-chargerProchainLotEcriture.json', HistoryJsonPage)
    profile = URL('/gae/afficherModificationMesDonnees.html', ProfileEntPage)

    subscription = URL(r'/Pgn/NavigationServlet\?MenuID=BANRELRIE&PageID=ReleveRIE&NumeroPage=1&Origine=Menu', SubscriptionPage)
    subscription_form = URL(r'Pgn/NavigationServlet', SubscriptionPage)

    def go_accounts(self):
        self.accounts.go()

    @need_login
    def get_accounts_list(self):
        accounts = []
        accounts.extend(self.accounts.stay_or_go().iter_accounts())
        for acc in self.balances.go().populate_balances(accounts):
            yield acc

    @need_login
    def iter_history(self, account):
        value = self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': 'valeur'}).get_value()
        for tr in self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': value}).iter_history(value=value):
            yield tr
        for tr in self.location('/icd/syd-front/data/syd-intraday-chargerDetail.json', data={'cl500_compte': account._id}).page.iter_history():
            yield tr

    @need_login
    def iter_subscription(self):
        subscriber = self.get_profile()

        self.subscription.go()

        for sub in self.page.iter_subscription():
            sub.subscriber = subscriber.name
            account = find_object(self.get_accounts_list(), id=sub.id, error=AccountNotFound)
            sub.label = account.label

            yield sub

    @need_login
    def iter_documents(self, subscription):
        data = {
            'PageID': 'ReleveRIE',
            'MenuID': 'BANRELRIE',
            'Origine': 'Menu',
            'compteSelected': subscription.id,
        }
        self.subscription_form.go(data=data)
        return self.page.iter_documents(sub_id=subscription.id)

class SGProfessionalBrowser(SGEnterpriseBrowser, StatesMixin):
    BASEURL = 'https://professionnels.secure.societegenerale.fr'
    LOGIN_FORM = 'auth_reco'
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'
    STATE_DURATION = 5

    incorrect_login = URL('/authent.html', IncorrectLoginPage)
    profile = URL('/gao/modifier-donnees-perso-saisie.html', ProfileProPage)

    transfer_dates = URL('/ord-web/ord//get-dates-execution.json', TransferDatesPage)
    easy_transfer = URL('/ord-web/ord//ord-virement-simplifie-emetteur.html', EasyTransferPage)
    internal_recipients = URL('/ord-web/ord//ord-virement-simplifie-beneficiaire.html', EasyTransferPage)
    external_recipients = URL('/ord-web/ord//ord-liste-compte-beneficiaire-externes.json', RecipientsJsonPage)

    init_transfer_page = URL('/ord-web/ord//ord-enregistrer-ordre-simplifie.json', TransferPage)
    sign_transfer_page = URL('/ord-web/ord//ord-verifier-habilitation-signature-ordre.json', SignTransferPage)
    confirm_transfer = URL('/ord-web/ord//ord-valider-signature-ordre.json', TransferPage)

    recipients = URL('/ord-web/ord//ord-gestion-tiers-liste.json', RecipientsJsonPage)
    add_recipient = URL('/ord-web/ord//ord-fragment-form-tiers.html\?cl_action=ajout&cl_idTiers=',
                        AddRecipientPage)
    add_recipient_step = URL('/ord-web/ord//ord-tiers-calcul-bic.json',
                             '/ord-web/ord//ord-preparer-signature-destinataire.json',
                             AddRecipientStepPage)
    confirm_new_recipient = URL('/ord-web/ord//ord-creer-destinataire.json', ConfirmRecipientPage)

    bank_statement_menu = URL('/icd/syd-front/data/syd-rce-accederDepuisMenu.json', BankStatementPage)
    bank_statement_search = URL('/icd/syd-front/data/syd-rce-lancerRecherche.json', BankStatementPage)

    date_max = None
    date_min = None

    new_rcpt_token = None
    new_rcpt_validate_form = None
    need_reload_state = None

    __states__ = ['need_reload_state', 'new_rcpt_token', 'new_rcpt_validate_form']

    def load_state(self, state):
        # reload state only for new recipient feature
        if state.get('need_reload_state'):
            state.pop('url', None)
            self.need_reload_state = None
            super(SGProfessionalBrowser, self).load_state(state)

    @need_login
    def iter_subscription(self):
        profile = self.get_profile()
        subscriber = profile.name

        self.bank_statement_menu.go()
        self.date_min, self.date_max = self.page.get_min_max_date()

        return self.page.iter_subscription(subscriber=subscriber)

    def get_month_by_range(self, end_month, month_range=3, january_limit=False):
        begin_month = ((end_month - month_range) % 12) + 1

        if january_limit:
            if begin_month >=end_month:
                return 1

        return begin_month

    def exceed_date_min(self, month_min, end_month):
        if end_month <= month_min:
            return True

    def advance_month(self, end_month, end_year, month_range=3):
        new_end_month = self.get_month_by_range(end_month, month_range)
        if new_end_month > end_month:
            end_year -= 1

        begin_month = self.get_month_by_range(new_end_month, month_range)
        begin_year = end_year
        if begin_month > new_end_month:
            begin_year -= 1

        return new_end_month, end_year, begin_month, begin_year

    def copy_recipient_obj(self, recipient):
        rcpt = Recipient()
        rcpt.id = recipient.iban
        rcpt.iban = recipient.iban
        rcpt.label = recipient.label
        rcpt.category = 'Externe'
        rcpt.enabled_at = date.today()
        return rcpt

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            self.validate_rcpt_with_sms(params['code'])
            return self.page.rcpt_after_sms(recipient)

        self.recipients.go()
        step_urls = {
            'first_recipient_check': self.absurl('/ord-web/ord//ord-valider-destinataire-avant-maj.json', base=True),
            'get_bic': self.absurl('/ord-web/ord//ord-tiers-calcul-bic.json', base=True),
            'get_token': self.absurl('/ord-web/ord//ord-preparer-signature-destinataire.json', base=True),
            'get_sign_info': self.absurl('/sec/getsigninfo.json', base=True),
            'send_otp_to_user': self.absurl('/sec/csa/send.json', base=True),
        }

        self.add_recipient.go(method='POST', headers={'Content-Type': 'application/json;charset=UTF-8'})
        countries = self.page.get_countries()

        # first recipient check
        data = {
            'an_codeAction': 'ajout_tiers',
            'an_refSICoordonnee': '',
            'an_refSITiers': '',
            'cl_iban': recipient.iban,
            'cl_raisonSociale': recipient.label,
        }
        self.location(step_urls['first_recipient_check'], data=data)

        # get bic
        data = {
            'an_activateCMU': 'true',
            'an_codePaysBanque': '',
            'an_nature': 'C',
            'an_numeroCompte': recipient.iban,
            'an_topIBAN': 'true',
            'cl_adresse': '',
            'cl_adresseBanque': '',
            'cl_codePays': recipient.iban[:2],
            'cl_libellePaysBanque': '',
            'cl_libellePaysDestinataire': countries[recipient.iban[:2]],
            'cl_nomBanque': '',
            'cl_nomRaisonSociale': recipient.label,
            'cl_ville': '',
            'cl_villeBanque': '',
        }
        self.location(step_urls['get_bic'], data=data)
        bic = self.page.get_response_data()

        # get token
        data = {
            'an_coordonnee_codePaysBanque': '',
            'an_coordonnee_nature': 'C',
            'an_coordonnee_numeroCompte': recipient.iban,
            'an_coordonnee_topConfidentiel': 'false',
            'an_coordonnee_topIBAN': 'true',
            'an_refSICoordonnee': '',
            'an_refSIDestinataire': '',
            'cl_adresse': '',
            'cl_codePays': recipient.iban[:2],
            'cl_coordonnee_adresseBanque': '',
            'cl_coordonnee_bic': bic,
            'cl_coordonnee_categories_libelle': '',
            'cl_coordonnee_categories_refSi': '',
            'cl_coordonnee_libellePaysBanque': '',
            'cl_coordonnee_nomBanque': '',
            'cl_coordonnee_villeBanque': '',
            'cl_libellePaysDestinataire': countries[recipient.iban[:2]],
            'cl_nomRaisonSociale': recipient.label,
            'cl_ville': '',
        }
        self.location(step_urls['get_token'], data=data)
        self.new_rcpt_validate_form = data
        payload = self.page.get_response_data()

        # get sign info
        data = {
            'b64_jeton_transaction': payload['jeton'],
            'action_level': payload['sensibilite'],
        }
        self.location(step_urls['get_sign_info'], data=data)

        # send otp to user
        data = {
            'context': payload['jeton'],
            'csa_op': 'sign'
        }
        self.location(step_urls['send_otp_to_user'], data=data)
        self.new_rcpt_validate_form.update(data)

        rcpt = self.copy_recipient_obj(recipient)
        self.need_reload_state = True
        raise AddRecipientStep(rcpt, Value('code', label='Veuillez entrer le code reçu par SMS.'))

    @need_login
    def validate_rcpt_with_sms(self, code):
        assert self.new_rcpt_validate_form, 'There should have recipient validate form in states'
        self.new_rcpt_validate_form.update({'code': code})
        try:
            self.confirm_new_recipient.go(data=self.new_rcpt_validate_form)
        except ClientError as e:
            assert e.response.status_code == 403, \
                'Something went wrong in add recipient, response status code is %s' % e.response.status_code
            raise AddRecipientBankError(message='Le code entré est incorrect.')

    @need_login
    def iter_recipients(self, origin_account):
        self.easy_transfer.go()
        self.page.update_origin_account(origin_account)

        if not hasattr(origin_account, '_product_code'):
            # check that origin account is updated, if not, this account can't do transfer
            return

        params = {
            'cl_ibanEmetteur': origin_account.iban,
            'cl_codeProduit': origin_account._product_code,
            'cl_codeSousProduit': origin_account._underproduct_code,
        }
        self.internal_recipients.go(method='POST', params=params, headers={'Content-Type': 'application/json;charset=UTF-8'})
        for internal_rcpt in self.page.iter_internal_recipients():
            yield internal_rcpt

        data = {
            'an_filtreIban': 'true',
            'an_filtreIbanSEPA': 'true',
            'an_isCredit': 'true',
            'an_isDebit': 'false',
            'an_rang': 0,
            'an_restrictFRMC': 'false',
            'cl_codeProduit': origin_account._product_code,
            'cl_codeSousProduit': origin_account._underproduct_code,
            'n_nbOccurences': '10000',
        }
        self.external_recipients.go(data=data)

        if self.page.is_external_recipients():
            assert self.page.is_all_external_recipient(), "Some recipients are missing"
            for external_rcpt in self.page.iter_external_recipients():
                yield external_rcpt

    @need_login
    def init_transfer(self, account, recipient, transfer):
        self.transfer_dates.go()
        if not self.page.is_date_valid(transfer.exec_date):
            raise TransferBankError(message="La date d'exécution du virement est invalide. Elle doit correspondre aux horaires et aux dates d'ouvertures d'agence.")

        # update account and recipient info
        recipient = find_object(self.iter_recipients(account), iban=recipient.iban, error=RecipientNotFound)

        data = [
            ('an_codeAction', 'C'),
            ('an_referenceSiOrdre', ''),
            ('cl_compteEmetteur_intitule', account._account_title),
            ('cl_compteEmetteur_libelle', account.label),
            ('an_compteEmetteur_iban', account.iban),
            ('cl_compteEmetteur_ibanFormate', account._formatted_iban),
            ('an_compteEmetteur_bic', account._bic),
            ('b64_compteEmetteur_idPrestation', account._id_service),
            ('an_guichetGestionnaire', account._manage_counter),
            ('an_codeProduit', account._product_code),
            ('an_codeSousProduit', account._underproduct_code),
            ('n_ordreMontantValeur', int(transfer.amount * (10 ** account._decimal_code))),
            ('n_ordreMontantCodeDecimalisation', account._decimal_code),
            ('an_ordreMontantCodeDevise', account._currency_code),
            ('cl_dateExecution', transfer.exec_date.strftime('%d/%m/%Y')),
            ('cl_ordreLibelle', transfer.label),
            ('an_beneficiaireCodeAction', 'C'),
            ('cl_beneficiaireRefSiCoordonnee', recipient._ref),
            ('cl_beneficiaireCompteLibelle', recipient.label),
            ('cl_beneficiaireCompteIntitule', recipient._account_title),
            ('cl_beneficiaireCompteIbanFormate', recipient._formatted_iban),
            ('an_beneficiaireCompteIban', recipient.iban),
            ('cl_beneficiaireCompteBic', recipient._bic),
            ('cl_beneficiaireAdressePays', recipient.iban[:2]),
            ('an_indicateurIntraAbonnement', 'false'),
            ('cl_reference', ' '),
            ('cl_motif', transfer.label),
        ]
        # WARNING: this save transfer information on user account
        self.init_transfer_page.go(data=data)
        return self.page.handle_response(account, recipient, transfer.amount, transfer.label, transfer.exec_date)

    @need_login
    def execute_transfer(self, transfer, **params):
        assert transfer._b64_id_transfer, 'Transfer token is missing'
        # get virtual keyboard
        data = {
            'b64_idOrdre': transfer._b64_id_transfer
        }
        self.sign_transfer_page.go(data=data)

        data.update(self.page.get_confirm_transfer_data(self.password))
        self.confirm_transfer.go(data=data)

        self.page.is_transfer_validated()
        return transfer

    @need_login
    def iter_documents(self, subscribtion):
        # This quality website can only fetch documents through a form, looking for dates
        # with a range of 3 months maximum

        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', self.date_max)
        end_day = int(m.group(1))
        end_month = int(m.group(2))
        end_year = int(m.group(3))

        month_range = 3
        begin_day = 2
        begin_month = self.get_month_by_range(end_month)
        begin_year = end_year
        if begin_month > end_month:
            begin_year -= 1

        # current month
        data = {
            'dt10_dateDebut' :'%02d/%02d/%d' % (begin_day, begin_month, begin_year),
            'dt10_dateFin': '%02d/%02d/%d' % (end_day, end_month, end_year),
            'cl2000_comptes': '["%s"]' % subscribtion.id,
            'cl200_typeRecherche': 'ADVANCED',
        }
        self.bank_statement_search.go(data=data)
        for d in self.page.iter_documents():
            yield d

        # other months
        m = re.search(r'(\d{2})/(\d{2})/(\d{4})', self.date_min)
        year_min = int(m.group(3))
        month_min = int(m.group(2))
        day_min = int(m.group(1))

        end_day = 1
        is_end = False
        while not is_end:
            end_month, end_year, begin_month, begin_year = self.advance_month(end_month, end_year, month_range)

            if year_min == begin_year and self.exceed_date_min(month_min, begin_month):
                begin_day = day_min
                begin_month = month_min
                is_end = True

            data = {
                'dt10_dateDebut' :'%02d/%02d/%d' % (begin_day, begin_month, begin_year),
                'dt10_dateFin': '%02d/%02d/%d' % (end_day, end_month, end_year),
                'cl2000_comptes': '["%s"]' % subscribtion.id,
                'cl200_typeRecherche': 'ADVANCED',
            }
            self.bank_statement_search.go(data=data)

            for d in self.page.iter_documents():
                yield d

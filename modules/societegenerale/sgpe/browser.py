# -*- coding: utf-8 -*-

# Copyright(C) 2013      Laurent Bachelier
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

from datetime import date
from dateutil.relativedelta import relativedelta

from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, NoAccountsException
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import (
    AccountNotFound, RecipientNotFound, AddRecipientStep, AddRecipientBankError,
    Recipient, TransferBankError, AccountOwnerType,
)
from weboob.tools.value import Value

from .pages import (
    LoginPage, CardsPage, CardHistoryPage, IncorrectLoginPage,
    ProfileProPage, ProfileEntPage, ChangePassPage, SubscriptionPage, InscriptionPage,
    ErrorPage, UselessPage, MainPage,
)
from .json_pages import (
    AccountsJsonPage, BalancesJsonPage, HistoryJsonPage, BankStatementPage,
    MarketAccountPage, MarketInvestmentPage,
)
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
    inscription_page = URL('/icd-web/gax/gax-inscription-utilisateur.html', InscriptionPage)

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

        if self.inscription_page.is_here():
            raise ActionNeeded(self.page.get_error())

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
        if account.type in (account.TYPE_MARKET, ):
            # market account transactions are in checking account
            return

        self.location('/Pgn/NavigationServlet?PageID=Cartes&MenuID=%sOPF&Classeur=1&NumeroPage=1&Rib=%s&Devise=%s' % (self.MENUID, account.id, account.currency))

        if self.inscription_page.is_here():
            raise ActionNeeded(self.page.get_error())

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
    MENUID = 'BANREL'
    CERTHASH = '2231d5ddb97d2950d5e6fc4d986c23be4cd231c31ad530942343a8fdcc44bb99'

    main_page = URL('/icd-web/syd-front/index-comptes.html', MainPage)

    accounts = URL('/icd/syd-front/data/syd-comptes-accederDepuisMenu.json', AccountsJsonPage)
    intraday_accounts = URL('/icd/syd-front/data/syd-intraday-accederDepuisMenu.json', AccountsJsonPage)

    balances = URL('/icd/syd-front/data/syd-comptes-chargerSoldes.json', BalancesJsonPage)
    intraday_balances = URL('/icd/syd-front/data/syd-intraday-chargerSoldes.json', BalancesJsonPage)

    history = URL('/icd/syd-front/data/syd-comptes-chargerReleve.json',
                  '/icd/syd-front/data/syd-intraday-chargerDetail.json', HistoryJsonPage)
    history_next = URL('/icd/syd-front/data/syd-comptes-chargerProchainLotEcriture.json', HistoryJsonPage)

    market_investment = URL(r'/Pgn/NavigationServlet\?.*PageID=CompteTitreDetailFrame',
                            r'/Pgn/NavigationServlet\?.*PageID=CompteTitreDetail',
                            MarketInvestmentPage)
    market_accounts = URL(r'/Pgn/NavigationServlet\?.*PageID=CompteTitreFrame',
                          r'/Pgn/NavigationServlet\?.*PageID=CompteTitre',
                          MarketAccountPage)

    profile = URL('/gae/afficherModificationMesDonnees.html', ProfileEntPage)

    subscription = URL(r'/Pgn/NavigationServlet\?MenuID=BANRELRIE&PageID=ReleveRIE&NumeroPage=1&Origine=Menu', SubscriptionPage)
    subscription_form = URL(r'Pgn/NavigationServlet', SubscriptionPage)

    def go_accounts(self):
        try:
            # get standard accounts
            self.accounts.go()
        except NoAccountsException:
            # get intraday accounts
            self.intraday_accounts.go()

    @need_login
    def get_accounts_list(self):
        # 'Comptes' are standard accounts on sge website
        # 'Opérations du jour' are intraday accounts on sge website
        # Standard and Intraday accounts are same accounts with different detail
        # User could have standard accounts with no intraday accounts or the contrary
        # They also could have both, in that case, retrieve only standard accounts
        try:
            # get standard accounts
            self.accounts.go()
            accounts = list(self.page.iter_class_accounts())
            self.balances.go()
        except NoAccountsException:
            # get intraday accounts
            self.intraday_accounts.go()
            accounts = list(self.page.iter_class_accounts())
            self.intraday_balances.go()

        for acc in self.page.populate_balances(accounts):
            acc.owner_type = AccountOwnerType.ORGANIZATION
            yield acc

        # retrieve market accounts if exist
        for market_account in self.iter_market_accounts():
            yield market_account

    @need_login
    def iter_history(self, account):
        if account.type in (account.TYPE_MARKET, ):
            # market account transactions are in checking account
            return

        value = self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': 'valeur'}).get_value()
        for tr in self.history.go(data={'cl500_compte': account._id, 'cl200_typeReleve': value}).iter_history(value=value):
            yield tr
        for tr in self.location('/icd/syd-front/data/syd-intraday-chargerDetail.json', data={'cl500_compte': account._id}).page.iter_history():
            yield tr

    @need_login
    def iter_market_accounts(self):
        self.main_page.go()
        # retrieve market accounts if exist
        market_accounts_link = self.page.get_market_accounts_link()

        # there are no examples of entreprise space with market accounts yet
        assert not market_accounts_link, 'There are market accounts, retrieve them.'
        return []

    @need_login
    def iter_investment(self, account):
        # there are no examples of entreprise space with market accounts yet
        return []

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
    MENUID = 'SBOREL'
    CERTHASH = '9f5232c9b2283814976608bfd5bba9d8030247f44c8493d8d205e574ea75148e'
    STATE_DURATION = 5

    incorrect_login = URL(r'/authent.html', IncorrectLoginPage)
    profile = URL(r'/gao/modifier-donnees-perso-saisie.html', ProfileProPage)

    transfer_dates = URL(r'/ord-web/ord//get-dates-execution.json', TransferDatesPage)
    easy_transfer = URL(r'/ord-web/ord//ord-virement-simplifie-emetteur.html', EasyTransferPage)
    internal_recipients = URL(r'/ord-web/ord//ord-virement-simplifie-beneficiaire.html', EasyTransferPage)
    external_recipients = URL(r'/ord-web/ord//ord-liste-compte-beneficiaire-externes.json', RecipientsJsonPage)

    init_transfer_page = URL(r'/ord-web/ord//ord-enregistrer-ordre-simplifie.json', TransferPage)
    sign_transfer_page = URL(r'/ord-web/ord//ord-verifier-habilitation-signature-ordre.json', SignTransferPage)
    confirm_transfer = URL(r'/ord-web/ord//ord-valider-signature-ordre.json', TransferPage)

    recipients = URL(r'/ord-web/ord//ord-gestion-tiers-liste.json', RecipientsJsonPage)
    add_recipient = URL(r'/ord-web/ord//ord-fragment-form-tiers.html\?cl_action=ajout&cl_idTiers=',
                        AddRecipientPage)
    add_recipient_step = URL(r'/ord-web/ord//ord-tiers-calcul-bic.json',
                             r'/ord-web/ord//ord-preparer-signature-destinataire.json',
                             AddRecipientStepPage)
    confirm_new_recipient = URL(r'/ord-web/ord//ord-creer-destinataire.json', ConfirmRecipientPage)

    bank_statement_menu = URL(r'/icd/syd-front/data/syd-rce-accederDepuisMenu.json', BankStatementPage)
    bank_statement_search = URL(r'/icd/syd-front/data/syd-rce-lancerRecherche.json', BankStatementPage)

    useless_page = URL(r'/icd-web/syd-front/index-comptes.html', UselessPage)
    error_page = URL(r'https://static.societegenerale.fr/pro/erreur.html', ErrorPage)

    markets_page = URL(r'/icd/npe/data/comptes-titres/findComptesTitresClasseurs-authsec.json', MarketAccountPage)
    investments_page = URL(r'/icd/npe/data/comptes-titres/findLignesCompteTitre-authsec.json', MarketInvestmentPage)

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
    def iter_market_accounts(self):
        self.markets_page.go()
        return self.page.iter_market_accounts()

    @need_login
    def iter_investment(self, account):
        if account.type not in (account.TYPE_MARKET, ):
            return []

        self.investments_page.go(data={'cl2000_numeroPrestation': account._prestation_number})
        return self.page.iter_investment()

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

        data = {
            'n_nbOccurences': 1000,
            'n_nbOccurences_affichees': 0,
            'n_rang': 0,
        }
        self.recipients.go(data=data)

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
        recipient = find_object(self.iter_recipients(account), iban=recipient.iban, id=recipient.id, error=RecipientNotFound)

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
            ('n_soldeComptableVeilleMontant', int(account.balance * (10 ** account._decimal_code))),
            ('n_soldeComptableVeilleCodeDecimalisation', account._decimal_code),
            ('an_soldeComptableVeilleDevise', account._currency_code),
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
            ('cl_beneficiaireDateCreation', recipient._created_date),
            ('cl_beneficiaireCodeOrigine', recipient._code_origin),
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
    def iter_subscription(self):
        profile = self.get_profile()
        subscriber = profile.name

        self.bank_statement_menu.go()
        self.date_min, self.date_max = self.page.get_min_max_date()
        return self.page.iter_subscription(subscriber=subscriber)

    @need_login
    def iter_documents(self, subscribtion):
        # This quality website can only fetch documents through a form, looking for dates
        # with a range of 3 months maximum
        search_date_max = self.date_max
        search_date_min = None
        is_end = False

        # to avoid infinite loop
        counter = 0

        while not is_end and counter < 50:
            # search for every 2 months
            search_date_min = search_date_max - relativedelta(months=2)

            if search_date_min < self.date_min:
                search_date_min = self.date_min
                is_end = True

            if search_date_max <= self.date_min:
                break

            data = {
                'dt10_dateDebut' : search_date_min.strftime('%d/%m/%Y'),
                'dt10_dateFin': search_date_max.strftime('%d/%m/%Y'),
                'cl2000_comptes': '["%s"]' % subscribtion.id,
                'cl200_typeRecherche': 'ADVANCED',
            }
            self.bank_statement_search.go(data=data)

            for d in self.page.iter_documents():
                yield d

            search_date_max = search_date_min - relativedelta(days=1)
            counter += 1

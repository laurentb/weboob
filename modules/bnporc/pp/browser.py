# -*- coding: utf-8 -*-

# Copyright(C) 2009-2016  Romain Bignon
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

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from requests.exceptions import ConnectionError

from weboob.browser.browsers import LoginBrowser, URL, need_login, StatesMixin
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import (
    AccountNotFound, Account, AddRecipientStep, AddRecipientTimeout,
    TransferInvalidRecipient, Loan,
)
from weboob.capabilities.bill import Subscription
from weboob.capabilities.profile import ProfileMissing
from weboob.tools.decorators import retry
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.browser.exceptions import ServerError
from weboob.browser.elements import DataError
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.tools.value import Value, ValueBool
from weboob.tools.capabilities.bank.investments import create_french_liquidity

from .pages import (
    LoginPage, AccountsPage, AccountsIBANPage, HistoryPage, TransferInitPage,
    ConnectionThresholdPage, LifeInsurancesPage, LifeInsurancesHistoryPage,
    LifeInsurancesDetailPage, NatioVieProPage, CapitalisationPage,
    MarketListPage, MarketPage, MarketHistoryPage, MarketSynPage, BNPKeyboard,
    RecipientsPage, ValidateTransferPage, RegisterTransferPage, AdvisorPage,
    AddRecipPage, ActivateRecipPage, ProfilePage, ListDetailCardPage, ListErrorPage,
    UselessPage, TransferAssertionError, LoanDetailsPage,
)

from .document_pages import DocumentsPage, DocumentsResearchPage, TitulairePage

__all__ = ['BNPPartPro', 'HelloBank']


class BNPParibasBrowser(LoginBrowser, StatesMixin):
    TIMEOUT = 30.0

    login = URL(
        r'identification-wspl-pres/identification\?acceptRedirection=true&timestamp=(?P<timestamp>\d+)',
        r'SEEA-pa01/devServer/seeaserver',
        r'https://mabanqueprivee.bnpparibas.net/fr/espace-prive/comptes-et-contrats\?u=%2FSEEA-pa01%2FdevServer%2Fseeaserver',
        LoginPage
    )

    list_error_page = URL(
        r'https://mabanque.bnpparibas/rsc/contrib/document/properties/identification-fr-part-V1.json', ListErrorPage
    )

    useless_page = URL(r'/fr/connexion/comptes-et-contrats', UselessPage)

    con_threshold = URL(
        r'/fr/connexion/100-connexions',
        r'/fr/connexion/mot-de-passe-expire',
        r'/fr/espace-prive/100-connexions.*',
        r'/fr/espace-pro/100-connexions-pro.*',
        r'/fr/espace-pro/changer-son-mot-de-passe',
        r'/fr/espace-client/100-connexions',
        r'/fr/espace-prive/mot-de-passe-expire',
        r'/fr/client/mdp-expire',
        r'/fr/client/100-connexion',
        r'/fr/systeme/page-indisponible',
        ConnectionThresholdPage
    )
    accounts = URL(r'udc-wspl/rest/getlstcpt', AccountsPage)
    loan_details = URL(r'caraccomptes-wspl/rpc/(?P<loan_type>.*)', LoanDetailsPage)
    ibans = URL(r'rib-wspl/rpc/comptes', AccountsIBANPage)
    history = URL(r'rop2-wspl/rest/releveOp', HistoryPage)
    history_old = URL(r'rop-wspl/rest/releveOp', HistoryPage)
    transfer_init = URL(r'virement-wspl/rest/initialisationVirement', TransferInitPage)

    lifeinsurances = URL(r'mefav-wspl/rest/infosContrat', LifeInsurancesPage)
    lifeinsurances_history = URL(r'mefav-wspl/rest/listMouvements', LifeInsurancesHistoryPage)
    lifeinsurances_detail = URL(r'mefav-wspl/rest/detailMouvement', LifeInsurancesDetailPage)

    natio_vie_pro = URL(r'/mefav-wspl/rest/natioViePro', NatioVieProPage)
    capitalisation_page = URL(
        r'https://www.clients.assurance-vie.fr/servlets/helios.cinrj.htmlnav.runtime.FrontServlet', CapitalisationPage
    )

    market_list = URL(r'pe-war/rpc/SAVaccountDetails/get', MarketListPage)
    market_syn = URL(r'pe-war/rpc/synthesis/get', MarketSynPage)
    market = URL(r'pe-war/rpc/portfolioDetails/get', MarketPage)
    market_history = URL(r'/pe-war/rpc/turnOverHistory/get', MarketHistoryPage)

    recipients = URL(r'/virement-wspl/rest/listerBeneficiaire', RecipientsPage)
    add_recip = URL(r'/virement-wspl/rest/ajouterBeneficiaire', AddRecipPage)
    activate_recip_sms = URL(r'/virement-wspl/rest/activerBeneficiaire', ActivateRecipPage)
    activate_recip_digital_key = URL(r'/virement-wspl/rest/verifierAuthentForte', ActivateRecipPage)
    validate_transfer = URL(r'/virement-wspl/rest/validationVirement', ValidateTransferPage)
    register_transfer = URL(r'/virement-wspl/rest/enregistrerVirement', RegisterTransferPage)

    advisor = URL(r'/conseiller-wspl/rest/monConseiller', AdvisorPage)

    titulaire = URL(r'/demat-wspl/rest/listerTitulairesDemat', TitulairePage)
    document = URL(r'/demat-wspl/rest/listerDocuments', DocumentsPage)
    document_research = URL(r'/demat-wspl/rest/rechercheCriteresDemat', DocumentsResearchPage)

    profile = URL(r'/kyc-wspl/rest/informationsClient', ProfilePage)
    list_detail_card = URL(r'/udcarte-wspl/rest/listeDetailCartes', ListDetailCardPage)

    STATE_DURATION = 10

    need_reload_state = False

    __states__ = ('need_reload_state', 'rcpt_transfer_id')

    def __init__(self, config, *args, **kwargs):
        super(BNPParibasBrowser, self).__init__(config['login'].get(), config['password'].get(), *args, **kwargs)
        self.accounts_list = None
        self.card_to_transaction_type = {}
        self.rotating_password = config['rotating_password'].get()
        self.digital_key = config['digital_key'].get()
        self.rcpt_transfer_id = None

    @retry(ConnectionError, tries=3)
    def open(self, *args, **kwargs):
        return super(BNPParibasBrowser, self).open(*args, **kwargs)

    def do_login(self):
        if not (self.username.isdigit() and self.password.isdigit()):
            raise BrowserIncorrectPassword()
        timestamp = lambda: int(time.time() * 1e3)
        self.login.go(timestamp=timestamp())
        if self.login.is_here():
            self.page.login(self.username, self.password)

    def load_state(self, state):
        # reload state only for new recipient feature
        if state.get('need_reload_state'):
            state.pop('url', None)
            self.need_reload_state = False
            super(BNPParibasBrowser, self).load_state(state)

    def change_pass(self, oldpass, newpass):
        res = self.open('/identification-wspl-pres/grille?accessible=false')
        url = '/identification-wspl-pres/grille/%s' % res.json()['data']['idGrille']
        keyboard = self.open(url)
        vk = BNPKeyboard(self, keyboard)
        data = {}
        data['codeAppli'] = 'PORTAIL'
        data['idGrille'] = res.json()['data']['idGrille']
        data['typeGrille'] = res.json()['data']['typeGrille']
        data['confirmNouveauPassword'] = vk.get_string_code(newpass)
        data['nouveauPassword'] = vk.get_string_code(newpass)
        data['passwordActuel'] = vk.get_string_code(oldpass)
        response = self.location('/mcs-wspl/rpc/modifiercodesecret', data=data)
        if response.json().get('messageIden').lower() == 'nouveau mot de passe invalide':
            return False
        return True

    @need_login
    def get_profile(self):
        self.profile.go(json={}, method='POST')
        profile = self.page.get_profile()
        if profile:
            return profile
        raise ProfileMissing(self.page.get_error_message())

    def is_loan(self, account):
        return account.type in (
            Account.TYPE_LOAN, Account.TYPE_MORTGAGE, Account.TYPE_CONSUMER_CREDIT, Account.TYPE_REVOLVING_CREDIT
        )

    @need_login
    def iter_accounts(self):
        if self.accounts_list is None:
            self.accounts_list = []
            # In case of password renewal, we need to go on ibans twice.
            self.ibans.go()
            ibans = self.page.get_ibans_dict() if self.ibans.is_here() else self.ibans.go().get_ibans_dict()
            # This page might be unavailable.
            try:
                ibans.update(self.transfer_init.go(json={'modeBeneficiaire': '0'}).get_ibans_dict('Crediteur'))
            except (TransferAssertionError, AttributeError):
                pass

            accounts = list(self.accounts.go().iter_accounts(ibans=ibans))
            self.market_syn.go(json={}, method='POST')  # do a post on the given URL
            market_accounts = self.page.get_list()  # get the list of 'Comptes Titres'
            checked_accounts = set()
            for account in accounts:
                if self.is_loan(account):
                    account = Loan.from_dict(account.to_dict())
                    if account.type in (Account.TYPE_MORTGAGE, Account.TYPE_CONSUMER_CREDIT):
                        self.loan_details.go(data={'iban': account.id}, loan_type='creditPret')
                        self.page.fill_loan_details(obj=account)

                    elif account.type == Account.TYPE_REVOLVING_CREDIT:
                        self.loan_details.go(data={'iban': account.id}, loan_type='creditConsoProvisio')
                        self.page.fill_revolving_details(obj=account)

                    elif account.type == Account.TYPE_LOAN:
                        self.loan_details.go(data={'iban': account.id}, loan_type='creditPretPersoPro')
                        self.page.fill_loan_details(obj=account)

                for market_acc in market_accounts:
                    if all((
                        market_acc['securityAccountNumber'].endswith(account.number[-4:]),
                        account.type in (Account.TYPE_MARKET, Account.TYPE_PEA),
                        account.label == market_acc['securityAccountName'],
                        not account.iban,
                    )):
                        if account.id in checked_accounts:
                            # in this case, we have identified two accounts for the same CompteTitre
                            raise DataError('we have two market accounts mapped to a same "CompteTitre" dictionary')

                        checked_accounts.add(account.id)
                        account.balance = market_acc.get('valorisation', account.balance)
                        account.valuation_diff = market_acc['profitLoss']
                        break
                self.accounts_list.append(account)

            # Fetching capitalisation contracts from the "Assurances Vie" space (some are not in the BNP API):
            params = self.natio_vie_pro.go().get_params()
            try:
                self.capitalisation_page.go(params=params)
            except ServerError:
                self.logger.warning("An Internal Server Error occurred")
            else:
                if self.capitalisation_page.is_here() and self.page.has_contracts():
                    for account in self.page.iter_capitalisation():
                        # Life Insurance accounts may appear BOTH in the API and the "Assurances Vie" domain,
                        # It is better to keep the API version since it contains the unitvalue:
                        if account.number not in [a.number for a in self.accounts_list]:
                            self.logger.warning("We found an account that only appears on the old BNP website.")
                            self.accounts_list.append(account)
                        else:
                            self.logger.warning("This account was skipped because it already appears in the API.")

        return iter(self.accounts_list)

    @need_login
    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    @need_login
    def iter_history(self, account, coming=False):
        # The accounts from the "Assurances Vie" space have no available history:
        if hasattr(account, '_details'):
            return []
        if account.type == Account.TYPE_PEA and account.label.endswith('Espèces'):
            return []
        if account.type == account.TYPE_LIFE_INSURANCE:
            return self.iter_lifeinsurance_history(account, coming)
        elif account.type in (account.TYPE_MARKET, Account.TYPE_PEA) and not coming:
            try:
                self.market_list.go(json={}, method='POST')
            except ServerError:
                self.logger.warning("An Internal Server Error occurred")
                return iter([])
            for market_acc in self.page.get_list():
                if account.number[-4:] == market_acc['securityAccountNumber'][-4:]:
                    self.page = self.market_history.go(
                        json={
                            "securityAccountNumber": market_acc['securityAccountNumber'],
                        }
                    )
                    return self.page.iter_history()
            return iter([])
        else:
            if not self.card_to_transaction_type:
                self.list_detail_card.go()
                self.card_to_transaction_type = self.page.get_card_to_transaction_type()
            data = {
                "ibanCrypte": account.id,
                "pastOrPending": 1,
                "triAV": 0,
                "startDate": (datetime.now() - relativedelta(years=1)).strftime('%d%m%Y'),
                "endDate": datetime.now().strftime('%d%m%Y')
            }
            try:
                self.history.go(json=data)
            except BrowserUnavailable:
                # old url is still used for certain connections bu we don't know which one is,
                # so the same HistoryPage is attained by the old url in another URL object
                data['startDate'] = (datetime.now() - relativedelta(years=3)).strftime('%d%m%Y')
                # old url authorizes up to 3 years of history
                self.history_old.go(data=data)

            if coming:
                return sorted_transactions(self.page.iter_coming())
            else:
                return sorted_transactions(self.page.iter_history())

    @need_login
    def iter_lifeinsurance_history(self, account, coming=False):
        self.lifeinsurances_history.go(json={
            "ibanCrypte": account.id,
        })

        for tr in self.page.iter_history(coming):
            page = self.lifeinsurances_detail.go(
                json={
                    "ibanCrypte": account.id,
                    "idMouvement": tr._op.get('idMouvement'),
                    "ordreMouvement": tr._op.get('ordreMouvement'),
                    "codeTypeMouvement": tr._op.get('codeTypeMouvement'),
                }
            )
            tr.investments = list(page.iter_investments())
            yield tr

    @need_login
    def iter_coming_operations(self, account):
        return self.iter_history(account, coming=True)

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_PEA and 'espèces' in account.label.lower():
            return [create_french_liquidity(account.balance)]

        # Life insurances and PERP may be scraped from the API or from the "Assurance Vie" space,
        # so we need to discriminate between both using account._details:
        if account.type in (account.TYPE_LIFE_INSURANCE, account.TYPE_PERP, account.TYPE_CAPITALISATION):
            if hasattr(account, '_details'):
                # Going to the "Assurances Vie" page
                natiovie_params = self.natio_vie_pro.go().get_params()
                self.capitalisation_page.go(params=natiovie_params)
                # Fetching the form to get the contract investments:
                capitalisation_params = self.page.get_params(account)
                self.capitalisation_page.go(params=capitalisation_params)
                return self.page.iter_investments()
            else:
                # No capitalisation contract has yet been found in the API:
                assert account.type != account.TYPE_CAPITALISATION
                self.lifeinsurances.go(json={
                    "ibanCrypte": account.id,
                })
                return self.page.iter_investments()

        elif account.type in (account.TYPE_MARKET, account.TYPE_PEA):
            try:
                self.market_list.go(json={}, method='POST')
            except ServerError:
                self.logger.warning("An Internal Server Error occurred")
                return iter([])
            for market_acc in self.page.get_list():
                if account.number[-4:] == market_acc['securityAccountNumber'][-4:] and not account.iban:
                    # Sometimes generate an Internal Server Error ...
                    try:
                        self.market.go(json={
                            "securityAccountNumber": market_acc['securityAccountNumber'],
                        })
                    except ServerError:
                        self.logger.warning("An Internal Server Error occurred")
                        break
                    return self.page.iter_investments()

        return iter([])

    @need_login
    def iter_recipients(self, origin_account_id):
        try:
            if (
                not origin_account_id in self.transfer_init.go(json={
                    'modeBeneficiaire': '0'
                }).get_ibans_dict('Debiteur')
            ):
                raise NotImplementedError()
        except TransferAssertionError:
            return

        # avoid recipient with same iban
        seen = set()
        for recipient in self.page.transferable_on(origin_account_ibancrypte=origin_account_id):
            if recipient.iban not in seen:
                seen.add(recipient.iban)
                yield recipient

        if self.page.can_transfer_to_recipients(origin_account_id):
            for recipient in self.recipients.go(json={'type': 'TOUS'}).iter_recipients():
                if recipient.iban not in seen:
                    seen.add(recipient.iban)
                    yield recipient

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            # for sms authentication
            return self.send_code(recipient, **params)

        # prepare commun data for all authentication method
        data = {}
        data['adresseBeneficiaire'] = ''
        data['iban'] = recipient.iban
        data['libelleBeneficiaire'] = recipient.label
        data['notification'] = True
        data['typeBeneficiaire'] = ''

        # provisional
        if self.digital_key:
            if 'digital_key' in params:
                return self.new_recipient_digital_key(recipient, data)

        # need to be on recipient page send sms or mobile notification
        # needed to get the phone number, enabling the possibility to send sms.
        # all users with validated phone number can receive sms code
        self.recipients.go(json={'type': 'TOUS'})

        # check type of recipient activation
        type_activation = 'sms'

        # provisional
        if self.digital_key:
            if self.page.has_digital_key():
                # force users with digital key activated to use digital key authentication
                type_activation = 'digital_key'

        if type_activation == 'sms':
            # post recipient data sending sms with same request
            data['typeEnvoi'] = 'SMS'
            recipient = self.add_recip.go(json=data).get_recipient(recipient)
            self.rcpt_transfer_id = recipient._transfer_id
            self.need_reload_state = True
            raise AddRecipientStep(recipient, Value('code', label='Saisissez le code reçu par SMS.'))
        elif type_activation == 'digital_key':
            # recipient validated with digital key are immediatly available
            recipient.enabled_date = datetime.today()
            raise AddRecipientStep(
                recipient,
                ValueBool(
                    'digital_key',
                    label=
                    'Validez pour recevoir une demande sur votre application bancaire. La validation de votre bénéficiaire peut prendre plusieurs minutes.'
                )
            )

    @need_login
    def send_code(self, recipient, **params):
        """
        add recipient with sms otp authentication
        """
        data = {}
        data['idBeneficiaire'] = self.rcpt_transfer_id
        data['typeActivation'] = 1
        data['codeActivation'] = params['code']
        self.rcpt_transfer_id = None
        return self.activate_recip_sms.go(json=data).get_recipient(recipient)

    @need_login
    def new_recipient_digital_key(self, recipient, data):
        """
        add recipient with 'clé digitale' authentication
        """
        # post recipient data, sending app notification with same request
        data['typeEnvoi'] = 'AF'
        self.add_recip.go(json=data)
        recipient = self.page.get_recipient(recipient)

        # prepare data for polling
        assert recipient._id_transaction
        polling_data = {}
        polling_data['idBeneficiaire'] = recipient._transfer_id
        polling_data['idTransaction'] = recipient._id_transaction
        polling_data['typeActivation'] = 2

        timeout = time.time() + 300.00  # float(second), like bnp website

        # polling
        while time.time() < timeout:
            time.sleep(5)  # like website
            self.activate_recip_digital_key.go(json=polling_data)
            if self.page.is_recipient_validated():
                break
        else:
            raise AddRecipientTimeout()

        return recipient

    @need_login
    def prepare_transfer(self, account, recipient, amount, reason, exec_date):
        data = {}
        data['devise'] = account.currency
        data['motif'] = reason
        data['dateExecution'] = exec_date.strftime('%d-%m-%Y')
        data['compteDebiteur'] = account.id
        data['montant'] = str(amount)
        data['typeVirement'] = 'SEPA'
        if recipient.category == u'Externe':
            data['idBeneficiaire'] = recipient._transfer_id
        else:
            data['compteCrediteur'] = recipient.id
        return data

    @need_login
    def init_transfer(self, account, recipient, amount, reason, exec_date):
        if recipient._web_state == 'En attente':
            raise TransferInvalidRecipient(message="Le bénéficiaire sélectionné n'est pas activé")

        data = self.prepare_transfer(account, recipient, amount, reason, exec_date)
        return self.validate_transfer.go(json=data).handle_response(account, recipient, amount, reason)

    @need_login
    def execute_transfer(self, transfer):
        self.register_transfer.go(json={'referenceVirement': transfer.id})
        return self.page.handle_response(transfer)

    @need_login
    def get_advisor(self):
        self.advisor.stay_or_go()
        if self.page.has_error():
            return None
        return self.page.get_advisor()

    @need_login
    def iter_threads(self):
        raise NotImplementedError()

    @need_login
    def get_thread(self, thread):
        raise NotImplementedError()

    @need_login
    def iter_documents(self, subscription):
        titulaires = self.titulaire.go().get_titulaires()
        # Calling '/demat-wspl/rest/listerDocuments' before the request on 'document'
        # is necessary when you specify an ikpi, otherwise no documents are returned
        self.document.go()
        docs = []
        id_docs = []
        iter_documents_functions = [self.page.iter_documents, self.page.iter_documents_pro]
        for iter_documents in iter_documents_functions:
            for doc in iter_documents(sub_id=subscription.id, sub_number=subscription._number, baseurl=self.BASEURL):
                docs.append(doc)
                id_docs.append(doc.id)

        # documents are sorted by type then date, sort them directly by date
        docs = sorted(docs, key=lambda doc: doc.date, reverse=True)
        for doc in docs:
            yield doc

        # When we only have one titulaire, no need to use the ikpi parameter in the request,
        # all document are provided with this simple request
        data = {
            'dateDebut': (datetime.now() - relativedelta(years=3)).strftime('%d/%m/%Y'),
            'dateFin': datetime.now().strftime('%d/%m/%Y'),
        }

        len_titulaires = len(titulaires)
        self.logger.info('The total number of titulaires on this connection is %s.', len_titulaires)
        # Ikpi is necessary for multi titulaires accounts to get each document of each titulaires
        if len_titulaires > 1:
            data['ikpiPersonne'] = subscription._iduser

        self.document_research.go(json=data)
        for doc in self.page.iter_documents(
            sub_id=subscription.id, sub_number=subscription._number, baseurl=self.BASEURL
        ):
            if doc.id not in id_docs:
                yield doc

    @need_login
    def iter_subscription(self):
        acc_list = self.iter_accounts()

        for acc in acc_list:
            sub = Subscription()
            sub.label = acc.label
            sub.subscriber = acc._subscriber
            sub.id = acc.id
            # number is the hidden number of an account like "****1234"
            # and it's used in the parsing of the docs in iter_documents
            sub._number = acc.number
            # iduser is the ikpi affiliate to the account,
            # usefull for multi titulaires connexions
            sub._iduser = acc._iduser
            yield sub


class BNPPartPro(BNPParibasBrowser):
    BASEURL_TEMPLATE = r'https://%s.bnpparibas/'
    BASEURL = BASEURL_TEMPLATE % 'mabanque'

    def __init__(self, config=None, *args, **kwargs):
        self.config = config
        super(BNPPartPro, self).__init__(self.config, *args, **kwargs)

    def switch(self, subdomain):
        self.BASEURL = self.BASEURL_TEMPLATE % subdomain


class HelloBank(BNPParibasBrowser):
    BASEURL = 'https://www.hellobank.fr/'

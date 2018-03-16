# -*- coding: utf-8 -*-

# Copyright(C) 2009-2016  Romain Bignon
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

from datetime import datetime
from dateutil.relativedelta import relativedelta
import time
from requests.exceptions import ConnectionError

from weboob.browser.browsers import LoginBrowser, URL, need_login
from weboob.capabilities.base import find_object
from weboob.capabilities.bank import AccountNotFound, Account, TransferError, AddRecipientStep
from weboob.tools.decorators import retry
from weboob.tools.json import json
from weboob.browser.exceptions import ServerError
from weboob.browser.elements import DataError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.value import Value

from .pages import LoginPage, AccountsPage, AccountsIBANPage, HistoryPage, TransferInitPage, \
                   ConnectionThresholdPage, LifeInsurancesPage, LifeInsurancesHistoryPage, \
                   LifeInsurancesDetailPage, MarketListPage, MarketPage, MarketHistoryPage, \
                   MarketSynPage, RecipientsPage, ValidateTransferPage, RegisterTransferPage, \
                   AdvisorPage, AddRecipPage, ActivateRecipPage, ProfilePage


__all__ = ['BNPPartPro', 'HelloBank']


def JSON(data):
    return ('json', data)


def isJSON(obj):
    return type(obj) is tuple and obj and obj[0] == 'json'


class JsonBrowserMixin(object):
    def open(self, *args, **kwargs):
        if isJSON(kwargs.get('data')):
            kwargs['data'] = json.dumps(kwargs['data'][1])
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Content-Type'] = 'application/json'

        return super(JsonBrowserMixin, self).open(*args, **kwargs)


class BNPParibasBrowser(JsonBrowserMixin, LoginBrowser):
    TIMEOUT = 30.0

    login = URL(r'identification-wspl-pres/identification\?acceptRedirection=true&timestamp=(?P<timestamp>\d+)',
                'SEEA-pa01/devServer/seeaserver',
                'https://mabanqueprivee.bnpparibas.net/fr/espace-prive/comptes-et-contrats\?u=%2FSEEA-pa01%2FdevServer%2Fseeaserver',
                LoginPage)
    con_threshold = URL('/fr/connexion/100-connexions',
                        '/fr/connexion/mot-de-passe-expire',
                        '/fr/espace-prive/100-connexions.*',
                        '/fr/espace-pro/100-connexions-pro.*',
                        '/fr/espace-pro/changer-son-mot-de-passe',
                        '/fr/espace-client/100-connexions',
                        '/fr/espace-prive/mot-de-passe-expire',
                        '/fr/systeme/page-indisponible', ConnectionThresholdPage)
    accounts = URL('udc-wspl/rest/getlstcpt', AccountsPage)
    ibans = URL('rib-wspl/rpc/comptes', AccountsIBANPage)
    history = URL('rop-wspl/rest/releveOp', HistoryPage)
    transfer_init = URL('virement-wspl/rest/initialisationVirement', TransferInitPage)

    lifeinsurances = URL('mefav-wspl/rest/infosContrat', LifeInsurancesPage)
    lifeinsurances_history = URL('mefav-wspl/rest/listMouvements', LifeInsurancesHistoryPage)
    lifeinsurances_detail = URL('mefav-wspl/rest/detailMouvement', LifeInsurancesDetailPage)

    market_list = URL('pe-war/rpc/SAVaccountDetails/get', MarketListPage)
    market_syn = URL('pe-war/rpc/synthesis/get', MarketSynPage)
    market = URL('pe-war/rpc/portfolioDetails/get', MarketPage)
    market_history = URL('/pe-war/rpc/turnOverHistory/get', MarketHistoryPage)

    recipients = URL('/virement-wspl/rest/listerBeneficiaire', RecipientsPage)
    add_recip = URL('/virement-wspl/rest/ajouterBeneficiaire', AddRecipPage)
    activate_recip = URL('/virement-wspl/rest/activerBeneficiaire', ActivateRecipPage)
    validate_transfer = URL('/virement-wspl/rest/validationVirement', ValidateTransferPage)
    register_transfer = URL('/virement-wspl/rest/enregistrerVirement', RegisterTransferPage)

    advisor = URL('/conseiller-wspl/rest/monConseiller', AdvisorPage)

    profile = URL(r'/kyc-wspl/rest/informationsClient', ProfilePage)

    accounts_list = None

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

    @need_login
    def get_profile(self):
        self.profile.go(data=JSON({}))
        profile = self.page.get_profile()
        if profile:
            return profile
        raise NotImplementedError()

    @need_login
    def get_accounts_list(self):
        if self.accounts_list is None:
            self.accounts_list = []
            # In case of password renewal, we need to go on ibans twice.
            self.ibans.go()
            ibans = self.page.get_ibans_dict() if self.ibans.is_here() else self.ibans.go().get_ibans_dict()
            # This page might be unavailable.
            try:
                ibans.update(self.transfer_init.go(data=JSON({'modeBeneficiaire': '0'})).get_ibans_dict('Crediteur'))
            except (TransferError, AttributeError):
                pass

            accounts = list(self.accounts.go().iter_accounts(ibans))
            self.market_syn.go(data=JSON({}))  # do a post on the given URL
            market_accounts = self.page.get_list()  # get the list of 'Comptes Titres'
            checked_accounts = set()
            for account in accounts:
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

        return iter(self.accounts_list)

    @need_login
    def get_account(self, _id):
        return find_object(self.get_accounts_list(), id=_id, error=AccountNotFound)

    @need_login
    def iter_history(self, account, coming=False):
        if account.type == Account.TYPE_PEA and account.label.endswith('Espèces'):
            return []
        if account.type == account.TYPE_LIFE_INSURANCE:
            return self.iter_lifeinsurance_history(account, coming)
        elif account.type in (account.TYPE_MARKET, Account.TYPE_PEA) and not coming:
            try:
                self.market_list.go(data=JSON({}))
            except ServerError:
                self.logger.warning("An Internal Server Error occured")
                return iter([])
            for market_acc in self.page.get_list():
                if account.number[-4:] == market_acc['securityAccountNumber'][-4:]:
                    self.page = self.market_history.go(data=JSON({
                        "securityAccountNumber": market_acc['securityAccountNumber'],
                    }))
                    return self.page.iter_history()
            return iter([])
        else:
            self.history.go(data=JSON({
                "ibanCrypte": account.id,
                "pastOrPending": 1,
                "triAV": 0,
                "startDate": (datetime.now() - relativedelta(years=2)).strftime('%d%m%Y'),
                "endDate": datetime.now().strftime('%d%m%Y')
            }))
        return self.page.iter_coming() if coming else self.page.iter_history()

    @need_login
    def iter_lifeinsurance_history(self, account, coming=False):
        self.lifeinsurances_history.go(data=JSON({
            "ibanCrypte": account.id,
        }))

        for tr in self.page.iter_history(coming):
            page = self.lifeinsurances_detail.go(data=JSON({
                "ibanCrypte": account.id,
                "idMouvement": tr._op.get('idMouvement'),
                "ordreMouvement": tr._op.get('ordreMouvement'),
                "codeTypeMouvement": tr._op.get('codeTypeMouvement'),
            }))
            tr.investments = list(page.iter_investments())
            yield tr


    @need_login
    def iter_coming_operations(self, account):
        return self.iter_history(account, coming=True)

    @need_login
    def iter_investment(self, account):
        if account.type == Account.TYPE_PEA and account.label.endswith('Espèces'):
            return []
        if account.type in (account.TYPE_LIFE_INSURANCE, account.TYPE_PERP):
            self.lifeinsurances.go(data=JSON({
                "ibanCrypte": account.id,
            }))
            return self.page.iter_investments()
        elif account.type in (account.TYPE_MARKET, account.TYPE_PEA):
            try:
                self.market_list.go(data=JSON({}))
            except ServerError:
                self.logger.warning("An Internal Server Error occured")
                return iter([])
            for market_acc in self.page.get_list():
                if account.number[-4:] == market_acc['securityAccountNumber'][-4:] and not account.iban:
                    # Sometimes generate an Internal Server Error ...
                    try:
                        self.market.go(data=JSON({
                            "securityAccountNumber": market_acc['securityAccountNumber'],
                        }))
                    except ServerError:
                        self.logger.warning("An Internal Server Error occured")
                        break
                    return self.page.iter_investments()
        return iter([])

    @need_login
    def iter_recipients(self, origin_account_id):
        try:
            if not origin_account_id in self.transfer_init.go(data=JSON({'modeBeneficiaire': '0'})).get_ibans_dict('Debiteur'):
                raise NotImplementedError()
        except TransferError:
            return

        for recipient in self.page.transferable_on(origin_account_ibancrypte=origin_account_id):
            yield recipient
        if self.page.can_transfer_to_recipients(origin_account_id):
            for recipient in self.recipients.go(data=JSON({'type': 'TOUS'})).iter_recipients():
                yield recipient

    @need_login
    def new_recipient(self, recipient, **params):
        if 'code' in params:
            return self.send_code(recipient, **params)
        # needed to get the phone number, enabling the possibility to send sms.
        self.recipients.go(data=JSON({'type': 'TOUS'}))
        # post recipient data sending sms with same request
        data = {}
        data['adresseBeneficiaire'] = ''
        data['iban'] = recipient.iban
        data['libelleBeneficiaire'] = recipient.label
        data['notification'] = True
        data['typeBeneficiaire'] = ''
        data['typeEnvoi'] = 'SMS'
        recipient = self.add_recip.go(data=json.dumps(data), headers={'Content-Type': 'application/json'}).get_recipient(recipient)
        raise AddRecipientStep(recipient, Value('code', label='Saisissez le code.'))

    @need_login
    def prepare_transfer(self, account, recipient, amount, reason):
        data = {}
        data['devise'] = account.currency
        data['motif'] = reason
        data['dateExecution'] = datetime.now().strftime('%d-%m-%Y')
        data['compteDebiteur'] = account.id
        data['montant'] = str(amount)
        data['typeVirement'] = 'SEPA'
        if recipient.category == u'Externe':
            data['idBeneficiaire'] = recipient.id
        else:
            data['compteCrediteur'] = recipient.id
        return data

    @need_login
    def init_transfer(self, account, recipient, amount, reason):
        data = self.prepare_transfer(account, recipient, amount, reason)
        return self.validate_transfer.go(data=JSON(data)).handle_response(account, recipient, amount, reason)

    @need_login
    def send_code(self, recipient, **params):
        # depending on whether recipient is a weboob or a budgea backend object.
        _id = recipient.webid if hasattr(recipient, 'webid') else recipient.id
        data = {}
        data['idBeneficiaire'] = _id
        data['typeActivation'] = 1
        data['codeActivation'] = params['code']
        return self.activate_recip.go(data=json.dumps(data), headers={'Content-Type': 'application/json'}).get_recipient(recipient)

    @need_login
    def execute_transfer(self, transfer):
        self.register_transfer.go(data=JSON({'referenceVirement': transfer.id}))
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


class BNPPartPro(BNPParibasBrowser):
    BASEURL_TEMPLATE = r'https://%s.bnpparibas/'
    BASEURL = BASEURL_TEMPLATE % 'mabanque'

    def __init__(self, config=None, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(BNPPartPro, self).__init__(*args, **kwargs)

    def switch(self, subdomain):
        self.BASEURL = self.BASEURL_TEMPLATE % subdomain


class HelloBank(BNPParibasBrowser):
    BASEURL = 'https://www.hellobank.fr/'

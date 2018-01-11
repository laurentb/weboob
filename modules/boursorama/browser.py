# -*- coding: utf-8 -*-

# Copyright(C) 2016       Baptiste Delpey
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


import requests
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from dateutil import parser

from weboob.browser.retry import login_method, retry_on_logout, RetryLoginBrowser
from weboob.browser.browsers import need_login, StatesMixin
from weboob.browser.url import URL
from weboob.exceptions import BrowserIncorrectPassword, BrowserHTTPNotFound
from weboob.browser.exceptions import LoggedOut
from weboob.capabilities.bank import (
    Account, AccountNotFound, TransferError, TransferInvalidAmount,
    TransferInvalidEmitter, TransferInvalidLabel, TransferInvalidRecipient,
    AddRecipientStep, Recipient,
)
from weboob.capabilities.contact import Advisor
from weboob.tools.captcha.virtkeyboard import VirtKeyboardError
from weboob.tools.value import Value
from weboob.tools.compat import basestring, urlsplit, urlunsplit

from .pages import (
    LoginPage, VirtKeyboardPage, AccountsPage, AsvPage, HistoryPage, AccbisPage, AuthenticationPage,
    MarketPage, LoanPage, SavingMarketPage, ErrorPage, IncidentPage, IbanPage, ProfilePage, ExpertPage,
    CardsNumberPage, CalendarPage, HomePage, PEPPage,
    TransferAccounts, TransferRecipients, TransferCharac, TransferConfirm, TransferSent,
    AddRecipientPage, RecipientCreated, StatusPage,
)


__all__ = ['BoursoramaBrowser']


class BrowserIncorrectAuthenticationCode(BrowserIncorrectPassword):
    pass


class BoursoramaBrowser(RetryLoginBrowser, StatesMixin):
    BASEURL = 'https://clients.boursorama.com'
    TIMEOUT = 60.0
    STATE_DURATION = 10

    home = URL('/$', HomePage)
    keyboard = URL('/connexion/clavier-virtuel\?_hinclude=300000', VirtKeyboardPage)
    status = URL(r'/aide/messages/dashboard\?showza=0&_hinclude=1', StatusPage)
    calendar = URL('/compte/cav/.*/calendrier', CalendarPage)
    error = URL('/connexion/compte-verrouille',
                '/infos-profil', ErrorPage)
    login = URL('/connexion/', LoginPage)
    accounts = URL('/dashboard/comptes\?_hinclude=300000', AccountsPage)
    pro_accounts = URL(r'/dashboard/comptes-professionnels\?_hinclude=1', AccountsPage)
    acc_tit = URL('/comptes/titulaire/(?P<webid>.*)\?_hinclude=1', AccbisPage)
    acc_rep = URL('/comptes/representative/(?P<webid>.*)\?_hinclude=1', AccbisPage)
    history = URL('/compte/(cav|epargne)/(?P<webid>.*)/mouvements.*',  HistoryPage)
    card_transactions = URL('/compte/cav/(?P<webid>.*)/carte/.*', HistoryPage)
    budget_transactions = URL('/budget/compte/(?P<webid>.*)/mouvements.*', HistoryPage)
    other_transactions = URL('/compte/cav/(?P<webid>.*)/mouvements.*', HistoryPage)
    saving_transactions = URL('/compte/epargne/csl/(?P<webid>.*)/mouvements.*', HistoryPage)
    saving_pep = URL('/compte/epargne/pep',  PEPPage)
    incident = URL('/compte/cav/(?P<webid>.*)/mes-incidents.*', IncidentPage)

    transfer_accounts = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/nouveau/(?P<id>\w+)/1',
                            TransferAccounts)
    recipients_page = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/$',
                          r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/nouveau/(?P<id>\w+)/2',
                          TransferRecipients)
    transfer_charac = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/nouveau/(?P<id>\w+)/3',
                          TransferCharac)
    transfer_confirm = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/nouveau/(?P<id>\w+)/4',
                           TransferConfirm)
    transfer_sent = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/nouveau/(?P<id>\w+)/5',
                        TransferSent)

    rcpt_created = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/comptes-externes/nouveau/(?P<id>\w+)/5',
                       RecipientCreated)
    rcpt_page = URL(r'/compte/(?P<type>[^/]+)/(?P<webid>\w+)/virements/comptes-externes/nouveau/(?P<id>\w+)/\d',
                    AddRecipientPage)

    asv = URL('/compte/assurance-vie/.*', AsvPage)
    saving_history = URL('/compte/cefp/.*/(positions|mouvements)',
                         '/compte/.*ord/.*/mouvements',
                         '/compte/pea/.*/mouvements',
                         '/compte/0%25pea/.*/mouvements',
                         '/compte/pea-pme/.*/mouvements', SavingMarketPage)
    market = URL('/compte/(?!assurance|cav|epargne).*/(positions|mouvements)',
                 '/compte/ord/.*/positions', MarketPage)
    loans = URL('/credit/immobilier/.*/informations',
                '/credit/consommation/.*/informations',
                '/credit/lombard/.*/caracteristiques', LoanPage)
    authentication = URL('/securisation', AuthenticationPage)
    iban = URL('/compte/(?P<webid>.*)/rib', IbanPage)
    profile = URL('/mon-profil/', ProfilePage)

    expert = URL('/compte/derive/', ExpertPage)

    cards = URL('/compte/cav/cb', CardsNumberPage)

    __states__ = ('auth_token',)

    def __init__(self, config=None, *args, **kwargs):
        self.config = config
        self.auth_token = None
        self.accounts_list = None
        self.deferred_card_calendar = None
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(BoursoramaBrowser, self).__init__(*args, **kwargs)

    def locate_browser(self, state):
        try:
            self.location(state['url'])
        except (requests.exceptions.HTTPError, requests.exceptions.TooManyRedirects, LoggedOut):
            pass

    def load_state(self, state):
        if ('expire' in state and parser.parse(state['expire']) > datetime.now()) or state.get('auth_token'):
            return super(BoursoramaBrowser, self).load_state(state)

    def handle_authentication(self):
        if self.authentication.is_here():
            if self.config['enable_twofactors'].get():
                self.page.sms_first_step()
                self.page.sms_second_step()
            else:
                raise BrowserIncorrectAuthenticationCode(
                    """Boursorama - activate the two factor authentication in boursorama config."""
                    """ You will receive SMS code but are limited in request per day (around 15)"""
                )

    @login_method
    def do_login(self):
        assert isinstance(self.config['device'].get(), basestring)
        assert isinstance(self.config['enable_twofactors'].get(), bool)
        if not self.password.isalnum():
            raise BrowserIncorrectPassword()

        if self.auth_token and self.config['pin_code'].get():
            self.page.authenticate()
        else:
            for _ in range(3):
                self.login.go()
                try:
                    self.page.login(self.username, self.password)
                except VirtKeyboardError:
                    self.logger.error('Failed to process VirtualKeyboard')
                else:
                    break
            else:
                raise VirtKeyboardError()

            if self.login.is_here() or self.error.is_here():
                raise BrowserIncorrectPassword()

            # After login, we might be redirected to the two factor authentication page.
            self.handle_authentication()

        if self.authentication.is_here():
            raise BrowserIncorrectAuthenticationCode('Invalid PIN code')

    def go_cards_number(self, link):
        self.location(link)
        self.location(self.page.get_cards_number_link())

    @retry_on_logout()
    @need_login
    def get_accounts_list(self):
        self.status.go()
        for x in range(3):
            if self.accounts_list is not None:
                break
            self.accounts_list = []
            self.accounts_list.extend(self.pro_accounts.go().iter_accounts())
            self.accounts_list.extend(self.accounts.go().iter_accounts())
            cards = [acc for acc in self.accounts_list if acc.type == Account.TYPE_CARD]
            if cards:
                self.go_cards_number(cards[0].url)
                if self.cards.is_here():
                    self.page.populate_cards_number(cards)

            for account in self.accounts_list:
                if account.type in [Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE]:
                    self.location(account.url)
                    if isinstance(self.page, MarketPage):
                        account.balance = self.page.get_balance(account.type) or account.balance

                if account.type != Account.TYPE_CARD:
                    account.iban = self.iban.go(webid=account._webid).get_iban()

            for card in cards:
                checking, = [account for account in self.accounts_list if account.type == Account.TYPE_CHECKING and account.url in card.url]
                card.parent = checking

        return self.accounts_list

    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a
        return None

    def get_debit_date(self, debit_date):
        for i, j in zip(self.deferred_card_calendar, self.deferred_card_calendar[1:]):
            if i[0].date() < debit_date <= j[0].date():
                return j[1].date()

    def get_card_transactions(self, account):
        self.location(account.url, params={'movementSearch[period]': 'currentPeriod'})
        if self.home.is_here():
            # for some cards, the site redirects us to '/'...
            return

        for t in self.page.iter_history(is_card=True):
            yield t

        params = {}
        params['movementSearch[toDate]'] = (date.today() + relativedelta(days=40)).strftime('%d/%m/%Y')
        params['movementSearch[fromDate]'] = (date.today() - relativedelta(years=3)).strftime('%d/%m/%Y')
        params['fullSearch'] = 1

        self.location(account.url, params=params)
        for t in self.page.iter_history(is_card=True, is_previous=True):
            yield t

    def get_invest_transactions(self, account, coming):
        if coming:
            return
        transactions = []
        self.location('%s/mouvements' % account.url.rstrip('/'))
        account._history_pages = []
        for t in self.page.iter_history(account=account):
            transactions.append(t)
        for t in self.page.get_transactions_from_detail(account):
            transactions.append(t)
        for t in sorted(transactions, key=lambda tr: tr.date, reverse=True):
            yield t

    def get_regular_transactions(self, account, coming):
        # We look for 3 years of history.
        params = {}
        params['movementSearch[toDate]'] = (date.today() + relativedelta(days=40)).strftime('%d/%m/%Y')
        params['movementSearch[fromDate]'] = (date.today() - relativedelta(years=3)).strftime('%d/%m/%Y')
        params['movementSearch[selectedAccounts][]'] = account._webid
        self.location('%s/mouvements' % account.url.rstrip('/'), params=params)
        for t in self.page.iter_history():
            yield t
        if coming and account.type == Account.TYPE_CHECKING:
            self.location('%s/mouvements-a-venir' % account.url.rstrip('/'), params=params)
            for t in self.page.iter_history(coming=True):
                yield t

    @retry_on_logout()
    @need_login
    def get_history(self, account, coming=False):
        if account.type is Account.TYPE_LOAN or '/compte/derive' in account.url:
            return []
        if account.type is Account.TYPE_SAVINGS and u"PLAN D'\xc9PARGNE POPULAIRE" in account.label:
            return []
        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            return self.get_invest_transactions(account, coming)
        elif account.type == Account.TYPE_CARD:
            return self.get_card_transactions(account)
        return self.get_regular_transactions(account, coming)

    @need_login
    def get_investment(self, account):
        if '/compte/derive' in account.url:
            return iter([])
        if not account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET, Account.TYPE_PEA):
            raise NotImplementedError()
        self.location(account.url)
        # We might deconnect at this point.
        if self.login.is_here():
            return self.get_investment(account)
        return self.page.iter_investment()

    @need_login
    def get_profile(self):
        return self.profile.stay_or_go().get_profile()

    @need_login
    def get_advisor(self):
        # same for everyone
        advisor = Advisor()
        advisor.name = u"Service clientèle"
        advisor.phone = u"0146094949"
        return iter([advisor])

    @need_login
    def iter_transfer_recipients(self, account):
        assert account.url

        url = urlsplit(account.url)
        parts = [part for part in url.path.split('/') if part]
        if account.type == Account.TYPE_SAVINGS:
            self.logger.debug('Deleting account name %s to get recipients', parts[-2])
            del parts[-2]

        parts.append('virements')
        url = url._replace(path='/'.join(parts))
        target = urlunsplit(url)

        try:
            self.location(target)
        except BrowserHTTPNotFound:
            return []

        if self.transfer_accounts.is_here():
            try:
                self.page.submit_account(account.id)
            except AccountNotFound:
                return []

        assert self.recipients_page.is_here()
        return self.page.iter_recipients()

    def check_basic_transfer(self, transfer):
        if transfer.amount <= 0:
            raise TransferInvalidAmount('transfer amount must be positive')
        if transfer.recipient_id == transfer.account_id:
            raise TransferInvalidRecipient('recipient must be different from emitter')
        if not transfer.label:
            raise TransferInvalidLabel('transfer label cannot be empty')

    @need_login
    def init_transfer(self, transfer, **kwargs):
        self.check_basic_transfer(transfer)

        account = self.get_account(transfer.account_id)
        if not account:
            raise AccountNotFound()

        recipients = list(self.iter_transfer_recipients(account))
        if not recipients:
            raise TransferInvalidEmitter('The account cannot emit transfers')

        recipients = [rcpt for rcpt in recipients if rcpt.id == transfer.recipient_id]
        if len(recipients) == 0:
            raise TransferInvalidRecipient('The recipient cannot be used with the emitter account')
        assert len(recipients) == 1

        self.page.submit_recipient(recipients[0]._tempid)
        assert self.transfer_charac.is_here()

        self.page.submit_info(transfer.amount, transfer.label, transfer.exec_date)
        assert self.transfer_confirm.is_here()

        ret = self.page.get_transfer()

        # at this stage, the site doesn't show the real ids/ibans, we can only guess
        if recipients[0].label != ret.recipient_label:
            if not recipients[0].label.startswith('%s - ' % ret.recipient_label):
                # the label displayed here is just "<name>"
                # but in the recipients list it is "<name> - <bank>"...
                raise TransferError('Recipient label changed during transfer')
        ret.recipient_id = recipients[0].id
        ret.recipient_iban = recipients[0].iban

        if account.label != ret.account_label:
            raise TransferError('Account label changed during transfer')

        ret.account_id = account.id
        ret.account_iban = account.iban

        return ret

    @need_login
    def execute_transfer(self, transfer, **kwargs):
        assert self.transfer_confirm.is_here()
        self.page.submit()

        assert self.transfer_sent.is_here()
        # the last page contains no info, return the last transfer object from init_transfer
        return transfer

    def build_recipient(self, recipient):
        r = Recipient()
        r.iban = recipient.iban
        r.id = recipient.iban
        r.label = recipient.label
        r.category = recipient.category
        r.enabled_at = date.today()
        r.currency = u'EUR'
        r.bank_name = recipient.bank_name
        return r

    @need_login
    def new_recipient(self, recipient, **kwargs):
        if 'code' in kwargs:
            assert self.rcpt_page.is_here()
            assert self.page.is_confirm_sms()

            self.page.confirm_sms(kwargs['code'])
            return self.rcpt_after_sms()

        account = None
        for account in self.get_accounts_list():
            if account.url:
                break

        suffix = 'virements/comptes-externes/nouveau'
        if account.url.endswith('/'):
            target = account.url + suffix
        else:
            target = account.url + '/' + suffix

        self.location(target)
        assert self.page.is_charac()

        self.page.submit_recipient(recipient)

        if self.page.is_send_sms():
            self.page.send_sms()
            assert self.page.is_confirm_sms()
            raise AddRecipientStep(self.build_recipient(recipient), Value('code', label='Veuillez saisir le code'))
        # if the add recipient is restarted after the sms has been confirmed recently, the sms step is not presented again

        return self.rcpt_after_sms()

    def rcpt_after_sms(self):
        assert self.page.is_confirm()

        ret = self.page.get_recipient()
        self.page.confirm()

        assert self.rcpt_created.is_here()
        return ret

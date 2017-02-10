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


from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from lxml.etree import XMLSyntaxError

from weboob.browser.browsers import LoginBrowser, need_login, StatesMixin
from weboob.browser.url import URL
from weboob.exceptions import BrowserIncorrectPassword, BrowserHTTPNotFound
from weboob.capabilities.bank import Account, AccountNotFound, TransferError
from weboob.tools.captcha.virtkeyboard import VirtKeyboardError

from .pages import (
    LoginPage, VirtKeyboardPage, AccountsPage, AsvPage, HistoryPage, AccbisPage, AuthenticationPage,
    MarketPage, LoanPage, SavingMarketPage, ErrorPage, IncidentPage, IbanPage, ProfilePage, ExpertPage,
    CardsNumberPage, CalendarPage, HomePage,
    TransferAccounts, TransferRecipients, TransferCharac, TransferConfirm, TransferSent,
)


__all__ = ['BoursoramaBrowser']


class BrowserIncorrectAuthenticationCode(BrowserIncorrectPassword):
    pass


class BoursoramaBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://clients.boursorama.com'
    TIMEOUT = 60.0

    home = URL('/$', HomePage)
    keyboard = URL('/connexion/clavier-virtuel\?_hinclude=300000', VirtKeyboardPage)
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
        self.webid = None
        self.accounts_list = None
        self.deferred_card_calendar = None
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(BoursoramaBrowser, self).__init__(*args, **kwargs)

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

    def do_login(self):
        assert isinstance(self.config['device'].get(), basestring)
        assert isinstance(self.config['enable_twofactors'].get(), bool)
        if not self.password.isdigit():
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

    @need_login
    def get_accounts_list(self):
        for x in range(3) :
            if self.accounts_list is not None:
                break
            self.accounts_list = []
            self.accounts_list.extend(self.pro_accounts.go().iter_accounts())
            self.accounts_list.extend(self.accounts.go().iter_accounts())
            self.acc_tit.go(webid=self.webid).populate(self.accounts_list)
            try:
                if not all([acc._webid for acc in self.accounts_list]):
                    self.acc_rep.go(webid=self.webid).populate(self.accounts_list)
            except XMLSyntaxError:
                self.accounts_list = None
                continue
            for account in self.accounts_list:
                account.iban = self.iban.go(webid=account._webid).get_iban()
        return iter(self.accounts_list)

    def get_account(self, id):
        assert isinstance(id, basestring)

        for a in self.get_accounts_list():
            if a.id == id:
                return a
        return None

    def get_closest(self, debit_date):
        debit_date = [dd for dd in self.deferred_card_calendar if debit_date <= dd <= debit_date + timedelta(days=7)]
        assert len(debit_date) == 1
        return debit_date[0]

    def get_card_transactions(self, account):
        self.location('%s' % account._link)
        if self.home.is_here():
            # for some cards, the site redirects us to '/'...
            return

        for t in self.page.iter_history(is_card=True):
            yield t

        self.location('%s' % account._link, params={'movementSearch[period]': 'previousPeriod'})
        for t in self.page.iter_history(is_card=True, is_previous=True):
            yield t

    def get_invest_transactions(self, account, coming):
        if coming:
            return
        transactions = []
        self.location('%s/mouvements' % account._link.rstrip('/'))
        account._history_pages = []
        for t in self.page.iter_history(account=account):
            transactions.append(t)
        for t in self.page.get_transactions_from_detail(account):
            transactions.append(t)
        for t in sorted(transactions, key=lambda tr: tr.date, reverse=True):
            yield t

    def get_regular_transactions(self, account, coming):
        # We look for 1 year of history.
        params = {}
        params['movementSearch[toDate]'] = (date.today() + relativedelta(days=40)).strftime('%d/%m/%Y')
        params['movementSearch[fromDate]'] = (date.today() - relativedelta(years=1)).strftime('%d/%m/%Y')
        params['movementSearch[selectedAccounts][]'] = account._webid
        self.location('%s/mouvements' % account._link.rstrip('/'), params=params)
        for t in self.page.iter_history():
            yield t
        if coming and account.type == Account.TYPE_CHECKING:
            self.location('%s/mouvements-a-venir' % account._link.rstrip('/'), params=params)
            for t in self.page.iter_history(coming=True):
                yield t

    @need_login
    def get_history(self, account, coming=False):
        if account.type is Account.TYPE_LOAN or '/compte/derive' in account._link:
            return []
        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            return self.get_invest_transactions(account, coming)
        elif account.type == Account.TYPE_CARD:
            return self.get_card_transactions(account)
        return self.get_regular_transactions(account, coming)

    @need_login
    def get_investment(self, account):
        if '/compte/derive' in account._link:
            return iter([])
        if not account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_MARKET):
            raise NotImplementedError()
        self.location(account._link)
        # We might deconnect at this point.
        if self.login.is_here():
            return self.get_investment(account)
        return self.page.iter_investment()

    @need_login
    def get_profile(self):
        return self.profile.stay_or_go().get_profile()

    @need_login
    def iter_transfer_recipients(self, account):
        assert account._link
        if account._link.endswith('/'):
            target = account._link + 'virements'
        else:
            target = account._link + '/virements'

        try:
            self.location(target)
        except BrowserHTTPNotFound:
            return []

        assert self.transfer_accounts.is_here()
        try:
            self.page.submit_account(account.id)
        except AccountNotFound:
            return []

        assert self.recipients_page.is_here()
        return self.page.iter_recipients()

    def check_basic_transfer(self, transfer):
        if transfer.amount <= 0:
            raise TransferError('transfer amount must be positive')
        if transfer.recipient_id == transfer.account_id:
            raise TransferError('recipient must be different from emitter')
        if not transfer.label:
            raise TransferError('transfer label cannot be empty')

    @need_login
    def init_transfer(self, transfer, **kwargs):
        self.check_basic_transfer(transfer)

        account = self.get_account(transfer.account_id)
        if not account:
            raise AccountNotFound()

        recipients = list(self.iter_transfer_recipients(account))
        if not recipients:
            raise TransferError('The account cannot emit transfers')

        recipients = [rcpt for rcpt in recipients if rcpt.id == transfer.recipient_id]
        if len(recipients) == 0:
            raise TransferError('The recipient cannot be used with the emitter account')
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
        ret = self.page.get_transfer()
        self.page.submit()

        assert self.transfer_sent.is_here()

        if transfer.account_iban and not ret.account_iban:
            account = self.get_account(transfer.account_id)
            ret.account_iban = account.iban

        return ret

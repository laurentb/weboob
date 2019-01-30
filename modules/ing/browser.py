# -*- coding: utf-8 -*-

# Copyright(C) 2009-2014  Florent Fourcot
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


import hashlib
import time
import json

from requests.exceptions import SSLError

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser.exceptions import ServerError
from weboob.capabilities.bank import Account, AccountNotFound
from weboob.capabilities.base import find_object, NotAvailable
from weboob.tools.capabilities.bank.transactions import FrenchTransaction

from .pages import (
    AccountsList, LoginPage, NetissimaPage, TitrePage,
    TitreHistory, TransferPage, BillsPage, StopPage, TitreDetails,
    TitreValuePage, ASVHistory, ASVInvest, DetailFondsPage, IbanPage,
    ActionNeededPage, ReturnPage, ProfilePage, LoanTokenPage, LoanDetailPage,
)

__all__ = ['IngBrowser']


def start_with_main_site(f):
    def wrapper(*args, **kwargs):
        browser = args[0]

        if browser.url and browser.url.startswith('https://bourse.ing.fr/'):
            for i in range(3):
                try:
                    browser.location('https://bourse.ing.fr/priv/redirectIng.php?pageIng=CC')
                except ServerError:
                    pass
                else:
                    break
            browser.where = 'start'
        elif browser.url and browser.url.startswith('https://ingdirectvie.ing.fr/'):
            browser.lifeback.go()
            browser.where = 'start'

        elif browser.url and browser.url.startswith('https://subscribe.ing.fr/'):
            browser.return_from_loan_site()

        return f(*args, **kwargs)
    return wrapper


class IngBrowser(LoginBrowser):
    BASEURL = 'https://secure.ing.fr'
    TIMEOUT = 60.0
    DEFERRED_CB = 'deferred'
    IMMEDIATE_CB = 'immediate'
    # avoid relogin every time
    lifeback = URL(r'https://ingdirectvie.ing.fr/b2b2c/entreesite/EntAccExit', ReturnPage)

    # Login and error
    loginpage = URL(r'/public/displayLogin.jsf.*', LoginPage)
    errorpage = URL(r'.*displayCoordonneesCommand.*', StopPage)
    actioneeded = URL(r'/general\?command=displayTRAlertMessage',
                      r'/protected/pages/common/eco1/moveMoneyForbidden.jsf', ActionNeededPage)

    # CapBank
    accountspage = URL(r'/protected/pages/index.jsf',
                       r'/protected/pages/asv/contract/(?P<asvpage>.*).jsf', AccountsList)
    titredetails = URL(r'/general\?command=display.*', TitreDetails)
    ibanpage = URL(r'/protected/pages/common/rib/initialRib.jsf', IbanPage)
    loantokenpage = URL(r'general\?command=goToConsumerLoanCommand&redirectUrl=account-details', LoanTokenPage)
    loandetailpage = URL(r'https://subscribe.ing.fr/consumerloan/consumerloan-v1/consumer/details', LoanDetailPage)
    # CapBank-Market
    netissima = URL(r'/data/asv/fiches-fonds/fonds-netissima.html', NetissimaPage)
    starttitre = URL(r'/general\?command=goToAccount&zone=COMPTE', TitrePage)
    titrepage = URL(r'https://bourse.ing.fr/priv/portefeuille-TR.php', TitrePage)
    titrehistory = URL(r'https://bourse.ing.fr/priv/compte.php\?ong=3', TitreHistory)
    titrerealtime = URL(r'https://bourse.ing.fr/streaming/compteTempsReelCK.php', TitrePage)
    titrevalue = URL(r'https://bourse.ing.fr/priv/fiche-valeur.php\?val=(?P<val>.*)&pl=(?P<pl>.*)&popup=1', TitreValuePage)
    asv_history = URL(r'https://ingdirectvie.ing.fr/b2b2c/epargne/CoeLisMvt',
                      r'https://ingdirectvie.ing.fr/b2b2c/epargne/CoeDetMvt', ASVHistory)
    asv_invest = URL(r'https://ingdirectvie.ing.fr/b2b2c/epargne/CoeDetCon', ASVInvest)
    detailfonds = URL(r'https://ingdirectvie.ing.fr/b2b2c/fonds/PerDesFac\?codeFonds=(.*)', DetailFondsPage)
    # CapDocument
    billpage = URL(r'/protected/pages/common/estatement/eStatement.jsf', BillsPage)
    # CapProfile
    profile = URL(r'/protected/pages/common/profil/(?P<page>\w+).jsf', ProfilePage)

    transfer = URL(r'/protected/pages/common/virement/index.jsf', TransferPage)

    __states__ = ['where']

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday')
        self.where = None
        LoginBrowser.__init__(self, *args, **kwargs)
        self.cache = {}
        self.cache["investments_data"] = {}
        self.only_deferred_cards = {}

        # will contain a list of the spaces
        # (the parameters needed to check and change them)
        # if not, it is an empty list
        self.multispace = None
        self.current_space = None

        # ing website is stateful, so we need to store the current subscription when download document to be sure
        # we download file for the right subscription
        self.current_subscription = None

    def do_login(self):
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        self.do_logout()
        self.loginpage.go()

        self.page.prelogin(self.username, self.birthday)
        self.page.login(self.password)
        if self.page.error():
            raise BrowserIncorrectPassword()
        if self.errorpage.is_here():
            raise BrowserIncorrectPassword('Please login on website to fill the form and retry')
        self.page.check_for_action_needed()

    @need_login
    def set_multispace(self):
        self.where = 'start'
        self.page.load_space_page()

        self.multispace = self.page.get_multispace()

        # setting the current_space depending on the current state of the page
        for space in self.multispace:
            if space['is_active']:
                self.current_space = space
                break

    @need_login
    def change_space(self, space):
        if self.multispace and not self.is_same_space(space, self.current_space):
            self.accountspage.go()
            self.where = 'start'
            self.page.load_space_page()

            self.page.change_space(space)
            self.current_space = space

    def is_same_space(self, a, b):
        return (
            a['name'] == b['name']
            and a['id'] == b['id']
            and a['form'] == b['form']
        )

    @start_with_main_site
    def get_market_balance(self, account):
        if self.where != 'start':
            self.accountspage.go()
            self.where = 'start'

        self.change_space(account._space)

        data = self.get_investments_data(account)
        for i in range(5):
            if i > 0:
                self.logger.debug("Can't get market balance, retrying in %s seconds...", (2**i))
                time.sleep(2**i)
            if self.accountspage.go(data=data).has_link():
                break

        self.starttitre.go()
        self.where = 'titre'
        self.titrepage.go()
        self.titrerealtime.go()
        account.balance = self.page.get_balance() or account.balance
        self.cache["investments_data"][account.id] = self.page.doc or None

    @need_login
    def fill_account(self, account):
        if account.type in [Account.TYPE_CHECKING, Account.TYPE_SAVINGS]:
            self.go_account_page(account)
            account.iban = self.ibanpage.go().get_iban()

        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            self.get_market_balance(account)

    @need_login
    def get_accounts_on_space(self, space, fill_account=True):
        accounts_list = []

        self.change_space(space)

        for acc in self.page.get_list():
            acc._space = space
            if fill_account:
                try:
                    self.fill_account(acc)
                except ServerError:
                    pass

            assert not find_object(accounts_list, id=acc.id), 'There is a duplicate account.'
            accounts_list.append(acc)
            yield acc

        for loan in self.iter_detailed_loans():
            loan._space = space
            assert not find_object(accounts_list, id=loan.id), 'There is a duplicate loan.'
            accounts_list.append(loan)
            yield loan


    @need_login
    @start_with_main_site
    def get_accounts_list(self, space=None, fill_account=True):
        self.accountspage.go()
        self.where = 'start'

        self.set_multispace()

        if space:
            for acc in self.get_accounts_on_space(space, fill_account=fill_account):
                yield acc

        elif self.multispace:
            for space in self.multispace:
                for acc in self.get_accounts_on_space(space, fill_account=fill_account):
                    yield acc
        else:
            for acc in self.page.get_list():
                acc._space = None
                if fill_account:
                    try:
                        self.fill_account(acc)
                    except ServerError:
                        pass
                yield acc

            for loan in self.iter_detailed_loans():
                loan._space = None
                yield loan

    @need_login
    @start_with_main_site
    def iter_detailed_loans(self):
        self.accountspage.go()
        self.where = 'start'

        for loan in self.page.get_detailed_loans():
            data = {'AJAXREQUEST': '_viewRoot',
                    'index': 'index',
                    'autoScroll': '',
                    'javax.faces.ViewState': loan._jid,
                    'accountNumber': loan._id,
                    'index:goToConsumerLoanUI': 'index:goToConsumerLoanUI'}

            self.accountspage.go(data=data)
            self.loantokenpage.go(data=data)
            try:
                self.loandetailpage.go()

            except ServerError as exception:
                json_error = json.loads(exception.response.text)
                if json_error['error']['code'] == "INTERNAL_ERROR":
                    raise BrowserUnavailable(json_error['error']['message'])
                raise
            else:
                self.page.getdetails(loan)
            yield loan
            self.return_from_loan_site()

    def return_from_loan_site(self):
        data = {'context': '{"originatingApplication":"SECUREUI"}',
                    'targetSystem': 'INTERNET'}
        self.location('https://subscribe.ing.fr/consumerloan/consumerloan-v1/sso/exit', data=data)
        self.location('https://secure.ing.fr/', data={'token': self.response.text})

    def get_account(self, _id, space=None):
        return find_object(self.get_accounts_list(fill_account=False, space=space), id=_id, error=AccountNotFound)

    def go_account_page(self, account):
        data = {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }
        self.accountspage.go(data=data)
        card_list = self.page.get_card_list()
        if card_list:
            self.only_deferred_cards[account._id] = all(
                [card['kind'] == self.DEFERRED_CB for card in card_list]
            )
        self.where = 'history'

    @need_login
    @start_with_main_site
    def get_coming(self, account):
        self.change_space(account._space)

        if account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()
        account = self.get_account(account.id, space=account._space)
        self.go_account_page(account)
        jid = self.page.get_history_jid()
        if jid is None:
            self.logger.info('There is no history for this account')
            return
        return self.page.get_coming()

    @need_login
    @start_with_main_site
    def get_history(self, account):
        self.change_space(account._space)

        if account.type in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            for result in self.get_history_titre(account):
                yield result
            return

        elif account.type != Account.TYPE_CHECKING and\
                account.type != Account.TYPE_SAVINGS:
            raise NotImplementedError()
        account = self.get_account(account.id, space=account._space)
        self.go_account_page(account)
        jid = self.page.get_history_jid()
        only_deferred_cb = self.only_deferred_cards.get(account._id)

        if jid is None:
            self.logger.info('There is no history for this account')
            return

        if account.type == Account.TYPE_CHECKING:
            history_function = AccountsList.get_transactions_cc
            index = -1  # disable the index. It works without it on CC
        else:
            history_function = AccountsList.get_transactions_others
            index = 0
        hashlist = set()
        while True:
            i = index
            for transaction in history_function(self.page, index=index):
                if only_deferred_cb and transaction.type == FrenchTransaction.TYPE_CARD:
                    transaction.type = FrenchTransaction.TYPE_DEFERRED_CARD

                transaction.id = hashlib.md5(transaction._hash).hexdigest()
                while transaction.id in hashlist:
                    transaction.id = hashlib.md5((transaction.id + "1").encode('ascii')).hexdigest()
                hashlist.add(transaction.id)
                i += 1
                yield transaction
            # if there is no more transactions, it is useless to continue
            if self.page.islast() or i == index:
                return
            if index >= 0:
                index = i
            data = {"AJAX:EVENTS_COUNT": 1,
                    "AJAXREQUEST": "_viewRoot",
                    "autoScroll": "",
                    "index": "index",
                    "index:%s:moreTransactions" % jid: "index:%s:moreTransactions" % jid,
                    "javax.faces.ViewState": account._jid
                    }
            self.accountspage.go(data=data)

    @need_login
    @start_with_main_site
    def iter_recipients(self, account):
        self.change_space(account._space)

        self.transfer.go()
        if not self.page.able_to_transfer(account):
            return iter([])

        self.page.go_to_recipient_selection(account)
        return self.page.get_recipients(origin=account)

    @need_login
    @start_with_main_site
    def init_transfer(self, account, recipient, transfer):
        self.change_space(account._space)

        self.transfer.go()
        self.page.do_transfer(account, recipient, transfer)
        return self.page.recap(account, recipient, transfer)

    @need_login
    @start_with_main_site
    def execute_transfer(self, transfer):
        self.page.confirm(self.password)
        return transfer

    def go_on_asv_detail(self, account, link):
        try:
            if self.page.asv_is_other:
                jid = self.page.get_asv_jid()
                data = {'index': "index", 'javax.faces.ViewState': jid, 'index:j_idcl': 'index:asvInclude:goToAsvPartner'}
                self.accountspage.go(data=data)
            else:
                self.accountspage.go(asvpage='manageASVContract')
                self.page.submit()
            self.page.submit()
            self.location(link)

            return True
        except SSLError:
            return False

    def get_investments_data(self, account):
        return {"AJAX:EVENTS_COUNT": 1,
                "AJAXREQUEST": "_viewRoot",
                "ajaxSingle": "index:setAccount",
                "autoScroll": "",
                "index": "index",
                "index:setAccount": "index:setAccount",
                "javax.faces.ViewState": account._jid,
                "cptnbr": account._id
                }

    def go_investments(self, account):
        account = self.get_account(account.id, space=account._space)

        data = self.get_investments_data(account)

        # On ASV pages, data maybe not available.
        for i in range(5):
            if i > 0:
                self.logger.debug('Investments list empty, retrying in %s seconds...', (2**i))
                time.sleep(2**i)

                if i > 1:
                    self.do_logout()
                    self.do_login()
                    account = self.get_account(account.id, space=account._space)
                    data['cptnbr'] = account._id
                    data['javax.faces.ViewState'] = account._jid

            self.accountspage.go(data=data)

            if not self.page.has_error():
                break

        else:
            self.logger.warning('Unable to get investments list...')

        if self.page.is_asv:
            return

        self.starttitre.go()
        self.where = 'titre'
        self.titrepage.go()

    @need_login
    @start_with_main_site
    def get_investments(self, account):
        if account.type not in (Account.TYPE_MARKET, Account.TYPE_PEA, Account.TYPE_LIFE_INSURANCE):
            raise NotImplementedError()

        self.go_investments(account)

        if self.where == 'titre':
            if self.cache['investments_data'].get(account.id) is None:
                self.titrerealtime.go()
            for inv in self.page.iter_investments(account):
                yield inv
        elif self.page.asv_has_detail or account._jid:
            self.accountspage.stay_or_go()
            shares = {}
            for asv_investments in self.page.iter_asv_investments():
                shares[asv_investments.label] = asv_investments.portfolio_share
            if self.go_on_asv_detail(account, '/b2b2c/epargne/CoeDetCon') is not False:
                self.where = 'asv'
                for inv in self.page.iter_investments():
                    inv.portfolio_share = shares[inv.label]
                    yield inv

    def get_history_titre(self, account):
        self.go_investments(account)

        if self.where == 'titre':
            self.titrehistory.go()
        elif self.page.asv_has_detail or account._jid:
            if self.go_on_asv_detail(account, '/b2b2c/epargne/CoeLisMvt') is False:
                return iter([])
        else:
            return iter([])

        transactions = list()
        # In order to reduce the amount of requests just to get ISIN codes, we fill
        # a dictionary with already visited investment pages and store their ISIN codes:
        isin_codes = {}
        for tr in self.page.iter_history():
            transactions.append(tr)
        if self.asv_history.is_here():
            for tr in transactions:
                page = tr._detail.result().page if tr._detail else None
                if page and 'numMvt' in page.url:
                    investment_list = list()
                    for inv in page.get_investments():
                        if inv._code_url in isin_codes:
                            inv.code = isin_codes.get(inv._code_url)
                        else:
                            # Fonds en euros (Eurossima) have no _code_url so we must set their code to None
                            if inv._code_url:
                                self.location(inv._code_url)
                                if self.detailfonds.is_here():
                                    inv.code = self.page.get_isin_code()
                                    isin_codes[inv._code_url] = inv.code
                                else:
                                    # In case the page is not available or blocked:
                                    inv.code = NotAvailable
                            else:
                                inv.code = None
                        investment_list.append(inv)
                    tr.investments = investment_list
            self.lifeback.go()
        return iter(transactions)

    ############# CapDocument #############
    @start_with_main_site
    @need_login
    def get_subscriptions(self):
        self.billpage.go()
        if self.loginpage.is_here():
            self.do_login()
            subscriptions = list(self.billpage.go().iter_subscriptions())
        else:
            subscriptions = list(self.page.iter_subscriptions())

        self.cache['subscriptions'] = {}
        for sub in subscriptions:
            self.cache['subscriptions'][sub.id] = sub

        return subscriptions

    def _go_to_subscription(self, subscription):
        # ing website is not stateless, make sure we are on the correct documents page before doing anything else
        if self.current_subscription and self.current_subscription.id == subscription.id:
            return

        self.billpage.go()
        data = {
            "AJAXREQUEST": "_viewRoot",
            "accountsel_form": "accountsel_form",
            subscription._formid: subscription._formid,
            "autoScroll": "",
            "javax.faces.ViewState": subscription._javax,
            "transfer_issuer_radio": subscription.id
        }
        self.billpage.go(data=data)
        self.current_subscription = subscription

    @need_login
    def get_documents(self, subscription):
        self._go_to_subscription(subscription)
        return self.page.iter_documents(subid=subscription.id)

    def download_document(self, bill):
        subid = bill.id.split('-')[0]
        # make sure we are on the right page to not download a document from another subscription
        self._go_to_subscription(self.cache['subscriptions'][subid])
        self.page.go_to_year(bill._year)
        return self.page.download_document(bill)

    ############# CapProfile #############
    @start_with_main_site
    @need_login
    def get_profile(self):
        profile = self.profile.go(page='coordonnees').get_profile()
        self.profile.go(page='infosperso').update_profile(profile)
        return profile

# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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
import json

from datetime import date
from functools import wraps

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.browser.exceptions import ClientError, ServerError
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.capabilities.bank import Account, Transaction, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.capabilities.bank.transactions import sorted_transactions

from .pages import (
    LogoutPage, AccountsPage, HistoryPage, LifeinsurancePage, MarketPage,
    AdvisorPage, LoginPage, ProfilePage,
)
from .transfer_pages import TransferInfoPage, RecipientsListPage, TransferPage


def retry(exc_check, tries=4):
    """Decorate a function to retry several times in case of exception.

    The decorated function is called at max 4 times. It is retried only when it
    raises an exception of the type `exc_check`.
    If the function call succeeds and returns an iterator, a wrapper to the
    iterator is returned. If iterating on the result raises an exception of type
    `exc_check`, the iterator is recreated by re-calling the function, but the
    values already yielded will not be re-yielded.
    For consistency, the function MUST always return values in the same order.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(browser, *args, **kwargs):
            cb = lambda: func(browser, *args, **kwargs)

            for i in range(tries, 0, -1):
                try:
                    ret = cb()
                except exc_check as exc:
                    browser.headers = None
                    browser.do_login()
                    browser.logger.info('%s raised, retrying', exc)
                    continue

                if not hasattr(ret, 'next'):
                    return ret  # simple value, no need to retry on items
                return iter_retry(cb, browser, value=ret, remaining=i, exc_check=exc_check, logger=browser.logger)

            raise BrowserUnavailable('Site did not reply successfully after multiple tries')

        return wrapper
    return decorator


class CmsoParBrowser(LoginBrowser, StatesMixin):
    __states__ = ('headers',)
    STATE_DURATION = 1
    headers = None

    login = URL('/securityapi/tokens',
                '/auth/checkuser', LoginPage)
    logout = URL('/securityapi/revoke',
                 '/auth/errorauthn',
                 '/\/auth/errorauthn', LogoutPage)
    accounts = URL('/domiapi/oauth/json/accounts/synthese(?P<type>.*)', AccountsPage)
    history = URL('/domiapi/oauth/json/accounts/(?P<page>.*)', HistoryPage)
    loans = URL('/creditapi/rest/oauth/v1/synthese', AccountsPage)
    lifeinsurance = URL('/assuranceapi/v1/oauth/sso/suravenir/DETAIL_ASSURANCE_VIE/(?P<accid>.*)',
                        'https://domiweb.suravenir.fr/', LifeinsurancePage)
    market = URL('/domiapi/oauth/json/ssoDomifronttitre',
                 'https://www.(?P<website>.*)/domifronttitre/front/sso/domiweb/01/(?P<action>.*)Portefeuille\?csrf=',
                 'https://www.*/domiweb/prive/particulier', MarketPage)
    advisor = URL('/edrapi/v(?P<version>\w+)/oauth/(?P<page>\w+)', AdvisorPage)

    # transfer
    transfer_info = URL(r'/domiapi/oauth/json/transfer/transferinfos', TransferInfoPage)
    recipients_list = URL(r'/domiapi/oauth/json/transfer/beneficiariesListTransfer', RecipientsListPage)
    init_transfer_page = URL(r'/domiapi/oauth/json/transfer/controlTransferOperation', TransferPage)
    execute_transfer_page = URL(r'/domiapi/oauth/json/transfer/transferregister', TransferPage)

    profile = URL(r'/domiapi/oauth/json/edr/infosPerson', ProfilePage)

    json_headers = {'Content-Type': 'application/json'}
    ARKEA = {'cmso.com': '03', 'cmb.fr': '01', 'cmmc.fr': '02', 'bpe.fr' : '08', 'arkeabanqueprivee.fr': '70',}

    def __init__(self, website, *args, **kwargs):
        super(CmsoParBrowser, self).__init__(*args, **kwargs)

        # Arkea Banque Privee uses specific URL prefix and name
        if website == 'arkeabanqueprivee.fr':
            self.BASEURL = "https://m.%s" % website
            self.name = 'abp'
        else:
            self.BASEURL = "https://mon.%s" % website
            self.name = website.split('.')[0]

        self.website = website
        self.arkea = self.ARKEA[website]
        self.accounts_list = []
        self.logged = False

    def do_login(self):
        if self.headers:
            self.session.headers = self.headers
        else:
            self.set_profile(self.PROFILE) # reset headers but don't clear them
            self.session.cookies.clear()
            self.accounts_list = []

            data = {
                'accessCode': self.username,
                'password': self.password,
                'clientId': 'com.arkea.%s.siteaccessible' % self.name,
                'redirectUri': '%s/auth/checkuser' % self.BASEURL,
                'errorUri': '%s/auth/errorauthn' % self.BASEURL
            }

            self.login.go(data=data)

            if self.logout.is_here():
                raise BrowserIncorrectPassword()

            m = re.search('access_token=([^&]+).*id_token=(.*)', self.url)

            self.session.headers.update({
                'Authentication': "Bearer %s" % m.group(2),
                'Authorization': "Bearer %s" % m.group(1),
                'X-ARKEA-EFS': self.arkea,
                'X-Csrf-Token': m.group(1)
            })

            self.headers = self.session.headers

    def get_account(self, _id):
        return find_object(self.iter_accounts(), id=_id, error=AccountNotFound)

    @retry((ClientError, ServerError))
    @need_login
    def iter_accounts(self):
        if self.accounts_list:
            return self.accounts_list

        seen = {}
        owner_name = self.get_profile().name.upper()

        self.transfer_info.go(json={"beneficiaryType":"INTERNATIONAL"})
        numbers = self.page.get_numbers()
        # to know if account can do transfer
        accounts_eligibilite_debit = self.page.get_eligibilite_debit()

        # First get all checking accounts...
        self.accounts.go(json={'typeListeCompte': 'COMPTE_SOLDE_COMPTES_CHEQUES'}, type='comptes')
        self.page.check_response()
        for key in self.page.get_keys():
            for a in self.page.iter_accounts(key=key):
                a._eligible_debit = accounts_eligibilite_debit.get(a.id, False)
                # Can have duplicate account, avoid them
                if a._index not in seen:
                    self.accounts_list.append(a)
                    seen[a._index] = a

        # Next, get saving accounts
        numbers.update(self.page.get_numbers())
        page = self.accounts.go(data=json.dumps({}), type='epargne', headers=self.json_headers)
        for key in page.get_keys():
            for a in page.iter_savings(key=key, numbers=numbers, name=owner_name):
                a._eligible_debit = accounts_eligibilite_debit.get(a.id, False)
                if a._index in seen:
                    acc = seen[a._index]
                    self.accounts_list.remove(acc)
                    self.logger.warning('replace %s because it seems to be a duplicate of %s', seen[a._index], a)
                self.accounts_list.append(a)

        # Then, get loans
        for key in self.loans.go().get_keys():
            for a in self.page.iter_loans(key=key):
                if a.id in seen:
                    self.logger.warning('skipping %s because it seems to be a duplicate of %s', seen[a.id], a)

                    account_found = False
                    for account in list(self.accounts_list):
                        # Loan id can be not unique when it also appears in json account page
                        if a.id == account._index:
                            account_found = True
                            # Merge information from account to loan
                            a.id = account.id
                            a.currency = account.currency
                            a.coming = account.coming
                            a.total_amount = account._total_amount
                            a._index = account._index
                            self.accounts_list.remove(account)
                            break
                    assert account_found

                self.accounts_list.append(a)
        return self.accounts_list

    def _go_market_history(self):
        content = self.market.go(data=json.dumps({'place': 'SITUATION_PORTEFEUILLE'}), headers=self.json_headers).text
        self.location(json.loads(content)['urlSSO'])

        return self.market.go(website=self.website, action='historique')

    @retry((ClientError, ServerError))
    @need_login
    def iter_history(self, account):
        account = self.get_account(account.id)

        if account.type in (Account.TYPE_LOAN, Account.TYPE_PEE):
            return iter([])

        if account.type == Account.TYPE_LIFE_INSURANCE:
            url = json.loads(self.lifeinsurance.go(accid=account._index).content)['url']
            url = self.location(url).page.get_link("opérations")

            return self.location(url).page.iter_history()
        elif account.type in (Account.TYPE_PEA, Account.TYPE_MARKET):
            self._go_market_history()
            if not self.page.go_account(account.label, account._owner):
                return []

            if not self.page.go_account_full():
                return []

            # Display code ISIN
            self.location(self.url, params={'reload': 'oui', 'convertirCode': 'oui'})
            # don't rely on server-side to do the sorting, not only do you need several requests to do so
            # but the site just toggles the sorting, resulting in reverse order if you browse multiple accounts
            return sorted_transactions(self.page.iter_history())

        # Getting a year of history
        nbs = ["UN", "DEUX", "TROIS", "QUATRE", "CINQ", "SIX", "SEPT", "HUIT", "NEUF", "DIX", "ONZE", "DOUZE"]
        trs = []

        self.history.go(data=json.dumps({"index": account._index}), page="pendingListOperations", headers=self.json_headers)

        has_deferred_cards = self.page.has_deferred_cards()

        self.history.go(data=json.dumps({'index': account._index}), page="detailcompte", headers=self.json_headers)

        self.trs = {'lastdate': None, 'list': []}

        for tr in self.page.iter_history(index=account._index, nbs=nbs):
            if has_deferred_cards and tr.type == Transaction.TYPE_CARD:
                tr.type = Transaction.TYPE_DEFERRED_CARD
                tr.bdate = tr.rdate

            trs.append(tr)

        return trs

    @retry((ClientError, ServerError))
    @need_login
    def iter_coming(self, account):
        account = self.get_account(account.id)

        if account.type is Account.TYPE_LOAN:
            return iter([])

        comings = []

        self.history.go(data=json.dumps({"index": account._index}), page="pendingListOperations", headers=self.json_headers)

        for key in self.page.get_keys():
            self.trs = {'lastdate': None, 'list': []}
            for c in self.page.iter_history(key=key):
                if hasattr(c, '_deferred_date'):
                    c.bdate = c.rdate
                    c.date = c._deferred_date
                    c.type = Transaction.TYPE_DEFERRED_CARD # force deferred card type for comings inside cards

                c.vdate = None # vdate don't work for comings

                comings.append(c)
        return iter(comings)

    @retry((ClientError, ServerError))
    @need_login
    def iter_investment(self, account):
        account = self.get_account(account.id)

        if account.type in (Account.TYPE_LIFE_INSURANCE, Account.TYPE_PERP):
            url = json.loads(self.lifeinsurance.go(accid=account._index).text)['url']
            url = self.location(url).page.get_link("supports")
            if not url:
                return iter([])
            return self.location(url).page.iter_investment()
        elif account.type in (Account.TYPE_MARKET, Account.TYPE_PEA):
            data = {"place": "SITUATION_PORTEFEUILLE"}
            response = self.market.go(data=json.dumps(data), headers=self.json_headers)
            self.location(json.loads(response.text)['urlSSO'])
            self.market.go(website=self.website, action="situation")
            if self.page.go_account(account.label, account._owner):
                return self.page.iter_investment()
            return []
        raise NotImplementedError()

    @retry((ClientError, ServerError))
    @need_login
    def iter_recipients(self, account):
        self.transfer_info.go(json={"beneficiaryType":"INTERNATIONAL"})

        if account.type in (Account.TYPE_LOAN, ):
            return
        if not account._eligible_debit:
            return

        # internal recipient
        for rcpt in self.page.iter_titu_accounts():
            if rcpt.id != account.id:
                yield rcpt
        for rcpt in self.page.iter_manda_accounts():
            if rcpt.id != account.id:
                yield rcpt
        for rcpt in self.page.iter_legal_rep_accounts():
            if rcpt.id != account.id:
                yield rcpt
        # external recipient
        for rcpt in self.page.iter_external_recipients():
            yield rcpt

    @need_login
    def init_transfer(self, account, recipient, amount, reason, exec_date):
        self.recipients_list.go(json={"beneficiaryType":"INTERNATIONAL"})

        transfer_data = {
            'beneficiaryIndex': self.page.get_rcpt_index(recipient),
            'debitAccountIndex': account._index,
            'devise': account.currency,
            'deviseReglement': account.currency,
            'montant': amount,
            'nature': 'externesepa',
            'transferToBeneficiary': True,
        }

        if exec_date and exec_date > date.today():
            transfer_data['date'] = int(exec_date.strftime('%s')) * 1000
        else:
            transfer_data['immediate'] =  True

        # check if recipient is internal or external
        if recipient.id != recipient.iban:
            transfer_data['nature'] = 'interne'
            transfer_data['transferToBeneficiary'] = False
            transfer_data['creditAccountIndex'] = transfer_data['beneficiaryIndex']
            transfer_data.pop('beneficiaryIndex')

        self.init_transfer_page.go(json=transfer_data)
        transfer = self.page.handle_transfer(account, recipient, amount, reason, exec_date)
        # transfer_data is used in execute_transfer
        transfer._transfer_data = transfer_data
        return transfer

    @need_login
    def execute_transfer(self, transfer, **params):
        assert transfer._transfer_data

        transfer._transfer_data.update({
            'enregistrerNouveauBeneficiaire': False,
            'creditLabel': 'de %s' % transfer.account_label if not transfer.label else transfer.label,
            'debitLabel': 'vers %s' % transfer.recipient_label,
            'typeFrais': 'SHA'
        })
        self.execute_transfer_page.go(json=transfer._transfer_data)
        transfer.id = self.page.get_transfer_confirm_id()
        return transfer

    @retry((ClientError, ServerError))
    @need_login
    def get_advisor(self):
        advisor = self.advisor.go(version="2", page="conseiller").get_advisor()
        return iter([self.advisor.go(version="1", page="agence").update_agency(advisor)])

    @retry((ClientError, ServerError))
    @need_login
    def get_profile(self):
        return self.profile.go(data=json.dumps({})).get_profile()


class iter_retry(object):
    # when the callback is retried, it will create a new iterator, but we may already yielded
    # some values, so we need to keep track of them and seek in the middle of the iterator

    def __init__(self, cb, browser, remaining=4, value=None, exc_check=Exception, logger=None):
        self.cb = cb
        self.it = value
        self.items = []
        self.remaining = remaining
        self.exc_check = exc_check
        self.logger = logger
        self.browser = browser
        self.delogged = False

    def __iter__(self):
        return self

    def __next__(self):
        if self.remaining <= 0:
            raise BrowserUnavailable('Site did not reply successfully after multiple tries')
        if self.delogged:
            self.browser.do_login()

        self.delogged = False

        if self.it is None:
            self.it = self.cb()

            # recreated iterator, consume previous items
            try:
                nb = -1
                for nb, sent in enumerate(self.items):
                    new = next(self.it)
                    if hasattr(new, 'iter_fields'):
                        equal = dict(sent.iter_fields()) == dict(new.iter_fields())
                    else:
                        equal = sent == new
                    if not equal:
                        # safety is not guaranteed
                        raise BrowserUnavailable('Site replied inconsistently between retries, %r vs %r', sent, new)
            except StopIteration:
                raise BrowserUnavailable('Site replied fewer elements (%d) than last iteration (%d)', nb + 1, len(self.items))
            except self.exc_check as exc:
                self.delogged = True
                if self.logger:
                    self.logger.info('%s raised, retrying', exc)
                self.it = None
                self.remaining -= 1
                return next(self)

        # return one item
        try:
            obj = next(self.it)
        except self.exc_check as exc:
            self.delogged = True
            if self.logger:
                self.logger.info('%s raised, retrying', exc)
            self.it = None
            self.remaining -= 1
            return next(self)
        else:
            self.items.append(obj)
            return obj

    next = __next__

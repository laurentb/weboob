# -*- coding: utf-8 -*-

# Copyright(C) 2013 Romain Bignon
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

import datetime

from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.exceptions import HTTPNotFound, ServerError
from weboob.browser.url import URL
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.compat import urlsplit, parse_qsl, urlencode

from .pages.base import (
    LoginPage, AccountsPage, TransactionsPage, WrongLoginPage, AccountSuspendedPage,
    AccountsPage2, ActionNeededPage, NoCardPage
)
from .pages.json import (
    AccountsPage3, JsonBalances, DashboardPage, JsonPeriods, JsonHistory,
    JsonBalances2, CurrencyPage
)


__all__ = ['AmericanExpressBrowser']


class AmericanExpressBrowser(LoginBrowser):
    BASEURL = 'https://global.americanexpress.com'

    login = URL('/myca/logon/.*', LoginPage)
    wrong_login = URL('/myca/fuidfyp/emea/.*', WrongLoginPage)
    account_suspended = URL('/myca/onlinepayments/', AccountSuspendedPage)
    partial_account = URL(r'/myca/intl/isummary/emea/summary.do\?method=reloadCardSummary&Face=fr_FR&sorted_index=(?P<idx>\d+)', AccountsPage)
    accounts = URL('/myca/intl/isummary/.*', AccountsPage)
    accounts2 = URL(r'/myca/intl/acctsumm/emea/accountSummary.do.*', AccountsPage2)

    transactions = URL('/myca/intl/estatement/.*', TransactionsPage)

    action_needed = URL(r'/myca/oce/emea/action/home\?request_type=un_Register', ActionNeededPage)

    # new site
    dashboard = URL(r'/dashboard', DashboardPage)
    accounts3 = URL(r'/accounts', AccountsPage3)
    js_balances = URL(r'/account-data/v1/financials/balances', JsonBalances)
    js_balances2 = URL(r'/api/servicing/v1/financials/transaction_summary\?type=split_by_cardmember&statement_end_date=(?P<date>[\d-]+)', JsonBalances2)
    js_pending = URL(r'/account-data/v1/financials/transactions\?limit=1000&offset=(?P<offset>\d+)&status=pending',
                     JsonHistory)
    js_posted = URL(r'/account-data/v1/financials/transactions\?limit=1000&offset=(?P<offset>\d+)&statement_end_date=(?P<end>[0-9-]+)&status=posted',
                    JsonHistory)
    js_periods = URL(r'/account-data/v1/financials/statement_periods', JsonPeriods)
    currency_page = URL(r'https://www.aexp-static.com/cdaas/axp-app/modules/axp-offers/1.11.1/fr-fr/axp-offers.json', CurrencyPage)

    no_card = URL('https://www.americanexpress.com/us/content/no-card/', NoCardPage)

    SUMMARY_CARD_LABEL = [
        u'PAYMENT RECEIVED - THANK YOU',
        u'PRELEVEMENT AUTOMATIQUE ENREGISTRE-MERCI'
    ]

    def __init__(self, *args, **kwargs):
        super(AmericanExpressBrowser, self).__init__(*args, **kwargs)
        self.cache = {}
        self.new_website = False

    def do_login(self):
        if not self.login.is_here():
            self.location('/myca/logon/emea/action?request_type=LogonHandler&DestPage=https%3A%2F%2Fglobal.americanexpress.com%2Fmyca%2Fintl%2Facctsumm%2Femea%2FaccountSummary.do%3Frequest_type%3D%26Face%3Dfr_FR%26intlink%3Dtopnavvotrecompteneligne-HPmyca&Face=fr_FR&Info=CUExpired')

        self.page.login(self.username, self.password)
        if self.wrong_login.is_here() or self.login.is_here() or self.account_suspended.is_here():
            raise BrowserIncorrectPassword()


    @need_login
    def go_on_accounts_list(self):
        if self.new_website:
            self.dashboard.go()
            assert self.dashboard.is_here()
            self.accounts3.go()
            return

        if self.transactions.is_here():
            form = self.page.get_form(name='leftnav')
            form.url = '/myca/intl/acctsumm/emea/accountSummary.do'
            form.submit()
        else:
            self.partial_account.go(idx='0')

    @need_login
    def get_accounts_new(self):
        self.transactions_url = 'https://global.americanexpress.com/myca/intl/estatement/emea/statement.do?request_type=&Face=fr_FR&account_key=%s&BPIndex=0&linknav=FR-myca-dashboard-estament-title' % (self.dashboard.go().get_user_key())
        self.accounts3.go()
        accounts = list(self.page.iter_accounts())

        for account in accounts:
            try:
                self.js_balances.go(headers={'account_tokens': account._token})
            except HTTPNotFound:
                self.js_periods.go(headers={'account_token': account._token})
                periods = self.page.get_periods()
                self.js_balances2.go(date=periods[1], headers={'account_tokens': account._token})
            self.page.set_balances(accounts)

        # get currency
        self.currency_page.go()
        currency = self.page.get_currency()

        for acc in accounts:
            acc.currency = currency
            yield acc

    @need_login
    def get_accounts_list(self):
        if self.new_website:
            for account in self.get_accounts_new():
                yield account
            return

        if not self.accounts.is_here() and not self.accounts2.is_here():
            self.go_on_accounts_list()

        if self.accounts2.is_here():
            for account in self.page.iter_accounts():
                yield account
            return

        for idx, cancelled in self.page.get_idx_list():
            account = self.get_account_by_idx(idx)
            if account.url or not cancelled:
                yield account

    @need_login
    def get_account_by_idx(self, idx):
        # xhr request fetching partial html of account info
        form = self.page.get_form(name='j-session-form')
        form.url = self.partial_account.build(idx=idx)
        form.submit()
        assert self.partial_account.is_here()

        return self.page.get_account()

    @need_login
    def iter_posted_new(self, account):
        self.js_periods.go(headers={'account_token': account._token})
        periods = self.page.get_periods()
        # TODO handle pagination
        try:
           #newwebsite
           # can't get transactions of some accounts on new website for the moment
            for p in periods:
                self.js_posted.go(offset=0, end=p, headers={'account_token': account._token})
                for tr in self.page.iter_history():
                    yield tr
        except ServerError:
            #old website
            if self.transactions_url:
                self.location(self.transactions_url)
                urls = self.page.get_next_url()
                for url in urls:
                    self.location(url)
                    for tr in self.page.get_history(account):
                        yield tr


    @need_login
    def iter_coming_new(self, account):
        # "pending" have no vdate and debit date is in future
        self.js_periods.go(headers={'account_token': account._token})
        date = datetime.datetime.strptime(self.page.get_periods()[0], '%Y-%m-%d').date()

        try:
            # can't get transactions of some accounts on new website for the moment
            self.js_pending.go(offset=0, headers={'account_token': account._token})
        except ServerError:
            return

        for tr in self.page.iter_history():
            tr.date = date
            yield tr

        # "posted" have a vdate but debit date can be future or past
        today = datetime.date.today()
        for tr in self.iter_posted_new(account):
            if tr.date > today:
                yield tr
            else:
                break

    @need_login
    def iter_coming(self, account):
        if self.new_website:
            for tr in self.iter_coming_new(account):
                yield tr
        else:
            for tr in self.iter_history_old(account):
                if tr._is_coming:
                    yield tr

    @need_login
    def iter_history(self, account):
        if self.new_website:
            today = datetime.date.today()
            for tr in self.iter_posted_new(account):
                if tr.date <= today:
                    yield tr
        else:
            for tr in self.iter_history_old(account):
                if not tr._is_coming:
                    yield tr

    @need_login
    def iter_history_old(self, account):
        if self.cache.get(account.id, None) is None:
            self.cache[account.id] = {}
            self.cache[account.id]["history"] = []
            if not self.accounts.is_here() and not self.accounts2.is_here():
                self.go_on_accounts_list()

            url = account.url
            if not url:
                return

            while url is not None:
                if self.accounts.is_here() or self.accounts2.is_here():
                    self.location(url)
                else:
                    form = self.page.get_form(name='leftnav')
                    form.url = url
                    form.submit()

                assert self.transactions.is_here()

                trs = sorted_transactions(self.page.get_history(account.currency))
                for tr in trs:
                    self.cache[account.id]["history"] += [tr]
                    yield tr

                if self.page.is_last():
                    url = None
                else:
                    v = urlsplit(url)
                    args = dict(parse_qsl(v.query))
                    args['BPIndex'] = int(args['BPIndex']) + 1
                    url = '%s?%s' % (v.path, urlencode(args))
        else:
            for tr in self.cache[account.id]["history"]:
                yield tr

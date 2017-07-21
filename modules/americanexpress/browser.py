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


from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.browser.url import URL
from weboob.tools.capabilities.bank.transactions import sorted_transactions
from weboob.tools.compat import urlsplit, parse_qsl, urlencode

from .pages import (
    LoginPage, AccountsPage, TransactionsPage, WrongLoginPage, AccountSuspendedPage,
    AccountsPage2, ActionNeededPage,
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

    def __init__(self, *args, **kwargs):
        super(AmericanExpressBrowser, self).__init__(*args, **kwargs)
        self.cache = {}

    def do_login(self):
        if not self.login.is_here():
            self.location('/myca/logon/emea/action?request_type=LogonHandler&DestPage=https%3A%2F%2Fglobal.americanexpress.com%2Fmyca%2Fintl%2Facctsumm%2Femea%2FaccountSummary.do%3Frequest_type%3D%26Face%3Dfr_FR%26intlink%3Dtopnavvotrecompteneligne-HPmyca&Face=fr_FR&Info=CUExpired')

        self.page.login(self.username, self.password)
        if self.wrong_login.is_here() or self.login.is_here() or self.account_suspended.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def go_on_accounts_list(self):
        if self.transactions.is_here():
            form = self.page.get_form(name='leftnav')
            form.url = '/myca/intl/acctsumm/emea/accountSummary.do'
            form.submit()
        else:
            self.partial_account.go(idx='0')

    @need_login
    def get_accounts_list(self):
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
    def get_history(self, account):
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

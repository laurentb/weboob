# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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

from datetime import timedelta, date, datetime
from dateutil import parser

from weboob.exceptions import NoAccountsException
from weboob.browser import PagesBrowser, URL, need_login, StatesMixin
from weboob.browser.selenium import SubSeleniumMixin
from weboob.browser.exceptions import LoggedOut, ClientError

from .pages.account_pages import (
    OtherPage, JsonAccSum, JsonAccHist
)

from .sbrowser import LoginBrowser

__all__ = ['HSBCHK']


class HSBCHK(StatesMixin, SubSeleniumMixin, PagesBrowser):
    BASEURL = 'https://www.services.online-banking.hsbc.com.hk/gpib/group/gpib/cmn/layouts/default.html?uid=dashboard'

    STATE_DURATION = 15

    app_gone = False

    acc_summary = URL(r'https://www.services.online-banking.hsbc.com.hk/gpib/channel/proxy/accountDataSvc/rtrvAcctSumm', JsonAccSum)
    acc_history = URL('https://www.services.online-banking.hsbc.com.hk/gpib/channel/proxy/accountDataSvc/rtrvTxnSumm', JsonAccHist)

    # catch-all
    other_page = URL(
        r' https://www.services.online-banking.hsbc.com.hk/gpib/systemErrorRedirect.html.*',
        OtherPage)

    __states__ = ('auth_token', 'logged', 'selenium_state')

    def __init__(self, username, password, secret, *args, **kwargs):
        super(HSBCHK, self).__init__(*args, **kwargs)
        # accounts index changes at each session
        self.accounts_dict_idx = None
        self.username = username
        self.password = password
        self.secret = secret
        self.logged = False
        self.auth_token = None

    def create_selenium_browser(self):
        dirname = self.responses_dirname
        if dirname:
            dirname += '/selenium'

        return LoginBrowser(
            self.username,
            self.password,
            self.secret,
            logger=self.logger,
            responses_dirname=dirname,
            proxy=self.PROXIES
        )

    def load_selenium_session(self, selenium):
        super(HSBCHK, self).load_selenium_session(selenium)
        self.location(
            selenium.url,
            referrer="https://www.security.online-banking.hsbc.com.hk/gsa/SaaS30Resource/"
        )

    def load_state(self, state):
        if ('expire' in state and parser.parse(state['expire']) > datetime.now()) or state.get('auth_token'):
            return super(HSBCHK, self).load_state(state)

    def open(self, *args, **kwargs):
        try:
            return super(HSBCHK, self).open(*args, **kwargs)
        except ClientError as e:
            if e.response.status_code == 401:
                self.auth_token = None
                self.logged = False
                self.session.cookies.clear()
                raise LoggedOut()
            if e.response.status_code == 409:
                raise NoAccountsException()
            raise

    def do_login(self):
        self.auth_token = None
        super(HSBCHK, self).do_login()
        self.auth_token = self.session.cookies.get('SYNC_TOKEN')
        self.logged = True

    @need_login
    def iter_accounts(self):
        # on new session initialize accounts dict
        if not self.accounts_dict_idx:
            self.accounts_dict_idx = dict()

        self.update_header()
        jq = {"accountSummaryFilter":{"txnTypCdes":[],"entityCdes":[{"ctryCde":"HK","grpMmbr":"HBAP"}]}}
        for a in self.acc_summary.go(json = jq).iter_accounts():
            self.accounts_dict_idx[a.id] = a
            yield a

    @need_login
    def get_history(self, account, coming=False, retry_li=True):
        if not self.accounts_dict_idx:
            self.iter_accounts()

        self.update_header()

        today = date.today()
        fromdate = today - timedelta(100)
        jq = {
            "retreiveTxnSummaryFilter": {
                "txnDatRnge": {
                    "fromDate": fromdate.isoformat(),
                    "toDate": today.isoformat()
                },
                "numOfRec": -1,
                "txnAmtRnge": None,
                "txnHistType": None  # "U"
            },
            "acctIdr": {
                "acctIndex": self.accounts_dict_idx[account.id]._idx,
                "entProdTypCde": account._entProdTypCde,
                "entProdCatCde": account._entProdCatCde
            },
            "pagingInfo": {
                "startDetail": None,
                "pagingDirectionCode": "PD"
            },
            "extensions": None
        }
        try:
            self.acc_history.go(json = jq)
        except NoAccountsException:
            return []
        return self.page.iter_history()

    def update_header(self):
        self.session.headers.update({
            "Origin":"https://www.services.online-banking.hsbc.com.hk",
            "Referer":"https://www.services.online-banking.hsbc.com.hk/gpib/group/gpib/cmn/layouts/default.html?uid=dashboard",
            "Content-type":"application/json",
            "X-HDR-Synchronizer-Token": self.session.cookies.get('SYNC_TOKEN')
        })

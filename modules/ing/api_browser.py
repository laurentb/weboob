# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import json
from collections import OrderedDict
from functools import wraps

from weboob.browser import LoginBrowser, URL
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, ActionNeeded
from weboob.browser.exceptions import ClientError

from .api import (
    LoginPage, AccountsPage, HistoryPage, ComingPage,
    DebitAccountsPage, CreditAccountsPage,
    ProfilePage,
)
from .web import StopPage, ActionNeededPage

from .browser import IngBrowser


def need_login(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        browser_conditions = (
            getattr(self, 'logged', False),
            getattr(self.old_browser, 'logged', False)
        )
        page_conditions = (
            (getattr(self, 'page', False) and self.page.logged),
            (getattr(self.old_browser, 'page', False) and self.old_browser.page.logged)
        )
        if not any(browser_conditions) and not any(page_conditions):
            self.do_login()

            if self.logger.settings.get('export_session'):
                self.logger.debug('logged in with session: %s', json.dumps(self.export_session()))
        return func(self, *args, **kwargs)

    return inner


def need_to_be_on_website(website):
    assert website in ('web', 'api')

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if website == 'web' and self.is_on_new_website:
                self.redirect_to_old_browser()
            elif website == 'api' and not self.is_on_new_website:
                self.redirect_to_api_browser()
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class IngAPIBrowser(LoginBrowser):
    BASEURL = 'https://m.ing.fr'

    # Login
    context = URL(r'/secure/api-v1/session/context')
    login = URL(r'/secure/api-v1/login/cif', LoginPage)
    keypad = URL(r'/secure/api-v1/login/keypad', LoginPage)
    pin_page = URL(r'/secure/api-v1/login/pin', LoginPage)

    # Error on old website
    errorpage = URL(r'https://secure.ing.fr/.*displayCoordonneesCommand.*', StopPage)
    actioneeded = URL(r'https://secure.ing.fr/general\?command=displayTRAlertMessage',
                      r'https://secure.ing.fr/protected/pages/common/eco1/moveMoneyForbidden.jsf', ActionNeededPage)

    # bank
    history = URL(r'/secure/api-v1/accounts/(?P<account_uid>.*)/transactions/after/(?P<tr_id>\d+)/limit/50', HistoryPage)
    coming = URL(r'/secure/api-v1/accounts/(?P<account_uid>.*)/futureOperations', ComingPage)
    accounts = URL(r'/secure/api-v1/accounts', AccountsPage)

    # transfer
    credit_accounts = URL(r'/secure/api-v1/transfers/debitAccounts/(?P<account_uid>.*)/creditAccounts', CreditAccountsPage)
    debit_accounts = URL(r'/secure/api-v1/transfers/debitAccounts', DebitAccountsPage)

    # profile
    informations = URL(r'/secure/api-v1/customer/info', ProfilePage)

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday')
        super(IngAPIBrowser, self).__init__(*args, **kwargs)

        self.old_browser = IngBrowser(*args, **kwargs)

    def handle_login_error(self, r):
        error_page = r.response.json()
        assert 'error' in error_page, "Something went wrong in login"
        error = error_page['error']

        if error['code'] == 'AUTHENTICATION.INVALID_PIN_CODE':
            raise BrowserIncorrectPassword(error['message'])
        elif error['code'] == 'AUTHENTICATION.ACCOUNT_INACTIVE':
            raise ActionNeeded(error['message'])
        assert error['code'] != 'INPUT_INVALID', error['message']
        raise BrowserUnavailable(error['message'])

    def do_login(self):
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        # login on new website
        # update cookies
        self.context.go()

        data = OrderedDict([
            ('birthDate', self.birthday),
            ('cif', self.username),
        ])
        try:
            self.login.go(json=data)
        except ClientError as e:
            self.handle_login_error(e)

        data = '{"keyPadSize":{"width":3800,"height":1520},"mode":""}'
        self.keypad.go(data=data, headers={'Content-Type': 'application/json'})

        img = self.open('/secure/api-v1/keypad/newkeypad.png').content
        data = {
            'clickPositions': self.page.get_password_coord(img, self.password)
        }

        try:
            self.pin_page.go(json=data, headers={'Referer': 'https://m.ing.fr/secure/login/pin'})
        except ClientError as e:
            self.handle_login_error(e)

        self.auth_token = self.page.response.headers['Ingdf-Auth-Token']
        self.session.headers['Ingdf-Auth-Token'] = self.auth_token
        self.session.cookies['ingdfAuthToken'] = self.auth_token

        # to be on logged page, to avoid relogin
        self.accounts.go()

    def deinit(self):
        self.old_browser.deinit()
        super(IngAPIBrowser, self).deinit()

    def redirect_to_old_browser(self):
        self.logger.info('Go on old website')
        token = self.location(
            '/secure/api-v1/sso/exit?context={"originatingApplication":"SECUREUI"}&targetSystem=INTERNET',
            method='POST'
        ).content
        data = {
            'token': token,
            'next': 'protected/pages/index.jsf',
            'redirectUrl': 'protected/pages/index.jsf',
            'targetApplication': 'INTERNET',
            'accountNumber': 'undefined'
        }
        self.session.cookies['produitsoffres'] = 'comptes'
        self.location('https://secure.ing.fr', data=data, headers={'Referer': 'https://secure.ing.fr'})
        self.old_browser.session.cookies.update(self.session.cookies)

    def redirect_to_api_browser(self):
        self.logger.info('Go on new website')
        self.old_browser.redirect_to_api_browser()
        self.session.cookies.update(self.old_browser.session.cookies)
        self.accounts.go()

    @property
    def is_on_new_website(self):
        return self.BASEURL in self.url

    ############# CapBank #############
    @need_to_be_on_website('web')
    def get_web_accounts(self):
        """iter accounts on old website"""
        return self.old_browser.get_accounts_list()

    @need_to_be_on_website('api')
    def get_api_accounts(self):
        """iter accounts on new website"""
        self.accounts.stay_or_go()
        return self.page.iter_accounts()

    @need_login
    def iter_matching_accounts(self):
        """Do accounts matching for old and new website"""

        api_accounts = [acc for acc in self.get_api_accounts()]

        # go on old website because new website have only cheking and card account information
        for web_acc in self.get_web_accounts():
            for api_acc in api_accounts:
                if web_acc.id[-4:] == api_acc.number[-4:]:
                    web_acc._uid = api_acc.id
                    yield web_acc
                    break
            else:
                assert False, 'There should be same account in web and api website'

    @need_to_be_on_website('web')
    def get_web_history(self, account):
        """iter history on old website"""
        return self.old_browser.get_history(account)

    @need_to_be_on_website('api')
    def get_api_history(self, account):
        """iter history on new website"""

        # first request transaction id is 0 to get the most recent transaction
        first_transaction_id = 0
        request_number_security = 0

        while request_number_security < 200:
            request_number_security += 1

            # first_transaction_id is 0 for the first request, then
            # it will decreasing after first_transaction_id become the last transaction id of the list
            self.history.go(account_uid=account._uid, tr_id=first_transaction_id)
            if self.page.is_empty_page():
                # empty page means that there are no more transactions
                break

            for tr in self.page.iter_history():
                # transaction id is decreasing
                first_transaction_id = int(tr.id)
                yield tr

            # like website, add 1 to the last transaction id of the list to get next transactions page
            first_transaction_id +=1

    @need_login
    def iter_history(self, account):
        """History switch"""

        if account.type not in (account.TYPE_CHECKING, ):
            return self.get_web_history(account)
        else:
            return self.get_api_history(account)

    @need_to_be_on_website('web')
    def get_web_coming(self, account):
        """iter coming on old website"""
        return self.old_browser.get_coming(account)

    @need_to_be_on_website('api')
    def get_api_coming(self, account):
        """iter coming on new website"""
        self.coming.go(account_uid=account._uid)
        return self.page.iter_coming()

    @need_login
    def iter_coming(self, account):
        """Incoming switch"""

        if account.type not in (account.TYPE_CHECKING, ):
            return self.get_web_coming(account)
        else:
            return self.get_api_coming(account)

    ############# CapWealth #############
    @need_login
    def get_investments(self, account):
        if account.type not in (account.TYPE_MARKET, account.TYPE_LIFE_INSURANCE, account.TYPE_PEA):
            return []

        # can't use `need_to_be_on_website`
        # because if return without iter invest on old website,
        # previous page is not handled by new website
        if self.is_on_new_website:
            self.redirect_to_old_browser()
        return self.old_browser.get_investments(account)

    ############# CapTransfer #############
    @need_login
    @need_to_be_on_website('api')
    def iter_recipients(self, account):
        self.debit_accounts.go()
        if account._uid not in self.page.get_debit_accounts_uid():
            return

        self.credit_accounts.go(account_uid=account._uid)
        for recipient in self.page.iter_recipients(acc_uid=account._uid):
            yield recipient

    @need_login
    def init_transfer(self, account, recipient, transfer):
        raise NotImplementedError()

    @need_login
    def execute_transfer(self, transfer):
        raise NotImplementedError()

    ############# CapDocument #############
    @need_login
    def get_subscriptions(self):
        raise BrowserUnavailable()

    @need_login
    def get_documents(self, subscription):
        raise BrowserUnavailable()

    def download_document(self, bill):
        raise BrowserUnavailable()

    ############# CapProfile #############
    @need_login
    def get_profile(self):
        self.informations.go()
        return self.page.get_profile()

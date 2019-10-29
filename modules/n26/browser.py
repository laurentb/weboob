# -*- coding: utf-8 -*-

# Copyright(C) 2016      Benjamin Bouvier
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

from decimal import Decimal
from datetime import datetime, timedelta

from weboob.browser import need_login
from weboob.browser.browsers import DomainBrowser, StatesMixin
from weboob.capabilities.base import find_object, NotAvailable
from weboob.capabilities.bank import Account, Transaction, AccountNotFound
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import (
    BrowserIncorrectPassword, BrowserUnavailable, BrowserQuestion, NeedInteractiveFor2FA,
)
from weboob.browser.exceptions import ClientError
from weboob.tools.value import Value

# Do not use an APIBrowser since APIBrowser sends all its requests bodies as
# JSON, although N26 only accepts urlencoded format.

class Number26Browser(DomainBrowser, StatesMixin):
    BASEURL = 'https://api.tech26.de'

    # Password encoded in base64 for the initial basic-auth scheme used to
    # get an access token.
    INITIAL_TOKEN = 'bXktdHJ1c3RlZC13ZHBDbGllbnQ6c2VjcmV0'
    __states__ = ('bearer', 'auth_method', 'mfaToken', 'refresh_token', 'token_expire')

    @property
    def logged(self):
        return self.token_expire and datetime.strptime(self.token_expire, '%Y-%m-%d %H:%M:%S') > datetime.now()

    def request(self, *args, **kwargs):
        """
        Makes it more convenient to add the bearer token and convert the result
        body back to JSON.
        """
        if not self.logged:
            kwargs.setdefault('headers', {})['Authorization'] = 'Basic ' + self.INITIAL_TOKEN
        else:
            kwargs.setdefault('headers', {})['Authorization'] = self.auth_method + ' ' + self.bearer
            kwargs.setdefault('headers', {})['Accept'] = "application/json"
        return self.open(*args, **kwargs).json()

    def __init__(self, config, *args, **kwargs):
        super(Number26Browser, self).__init__(*args, **kwargs)
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        self.auth_method = 'Basic'
        self.refresh_token = None
        self.token_expire = None
        self.mfaToken = None
        self.bearer = self.INITIAL_TOKEN

    def do_otp(self, mfaToken):
        data = {
            'challengeType': 'otp',
            'mfaToken': mfaToken
        }
        try:
            result = self.request('/api/mfa/challenge', json=data)
        except ClientError as e:
            response = e.response.json()
            # if we send more than 5 otp without success, the server will warn the user to
            # wait 12h before retrying, but in fact it seems that we can resend otp 5 mins later
            if e.response.status_code == 429:
                raise BrowserUnavailable(response['detail'])
        raise BrowserQuestion(Value('otp', label='Veuillez entrer le code reçu par sms au ' + result['obfuscatedPhoneNumber']))

    def update_token(self, auth_method, bearer, refresh_token, expires_in):
        self.auth_method = auth_method
        self.bearer = bearer
        self.refresh_token = refresh_token
        if expires_in is not None:
            self.token_expire = (datetime.now() + timedelta(seconds=expires_in)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            self.token_expire = None

    def has_refreshed(self):
        data = {
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        try:
            result = self.request('/oauth2/token', data=data)
        except ClientError as e:
            if e.response.status_code == 401:
                self.update_token('Basic', self.INITIAL_TOKEN, None, None)
                return False
            else:
                assert False, 'Unhandled error: %s' % e.response.status_code
        self.update_token(result['token_type'], result['access_token'], result['refresh_token'], result['expires_in'])
        return True

    def do_login(self):
        # The refresh token last between one and two hours, be carefull, otp asked frequently
        if self.refresh_token:
            if self.has_refreshed():
                return

        if self.config['request_information'].get() is None:
            raise NeedInteractiveFor2FA()

        if self.config['otp'].get():
            data = {
                'mfaToken': self.mfaToken,
                'grant_type': 'mfa_otp',
                'otp': self.config['otp'].get()
            }
        else:
            data = {
                'username': self.username,
                'password': self.password,
                'grant_type': 'password'
            }

        try:
            result = self.request('/oauth2/token', data=data)
        except ClientError as ex:
            response = ex.response.json()
            if response.get('title') == 'A second authentication factor is required.':
                self.mfaToken = response.get('mfaToken')
                self.do_otp(self.mfaToken)
            elif response.get('error') == 'invalid_grant':
                raise BrowserIncorrectPassword(response['error_description'])
            elif response.get('title') == 'Error':
                raise BrowserUnavailable(response['message'])
            elif response.get('title') == 'invalid_otp':
                raise BrowserIncorrectPassword(response['userMessage']['detail'])
            # if we try too many requests, it will return a 429 and the user will have
            # to wait 30 minutes before retrying, and if he retries at 29 min, he will have
            # to wait 30 minutes more
            elif ex.response.status_code == 429:
                raise BrowserUnavailable(response['detail'])
            else:
                assert False, "Unhandled error on '/oauth2/token' request"

        self.update_token(result['token_type'], result['access_token'], result['refresh_token'], result['expires_in'])

    @need_login
    def get_accounts(self):
        account = self.request('/api/accounts')
        spaces = self.request('/api/spaces')

        a = Account()

        # Number26 only provides a checking account (as of sept 19th 2016).
        a.type = Account.TYPE_CHECKING
        a.label = u'Checking account'

        a.id = account["id"]
        a.number = NotAvailable
        a.balance = Decimal(str(spaces["totalBalance"]))
        a.iban = account["iban"]
        a.currency = u'EUR'

        return [a]

    @need_login
    def get_account(self, _id):
        return find_object(self.get_accounts(), id=_id, error=AccountNotFound)

    @need_login
    def get_categories(self):
        """
        Generates a map of categoryId -> categoryName, for fast lookup when
        fetching transactions.
        """
        categories = self.request('/api/smrt/categories')

        cmap = {}
        for c in categories:
            cmap[c["id"]] = c["name"]

        return cmap

    @staticmethod
    def is_past_transaction(t):
        return "userAccepted" in t or "confirmed" in t

    @need_login
    def get_transactions(self, categories):
        return self._internal_get_transactions(categories, Number26Browser.is_past_transaction)

    @need_login
    def get_coming(self, categories):
        filter = lambda x: not Number26Browser.is_past_transaction(x)
        return self._internal_get_transactions(categories, filter)

    @need_login
    def _internal_get_transactions(self, categories, filter_func):
        TYPES = {
            'PT': Transaction.TYPE_CARD,
            'AA': Transaction.TYPE_CARD,
            'CT': Transaction.TYPE_TRANSFER,
            'WEE': Transaction.TYPE_BANK,
        }

        transactions = self.request('/api/smrt/transactions?limit=1000')

        for t in transactions:

            if not filter_func(t) or t["amount"] == 0:
                continue

            new = Transaction()

            new.date = datetime.fromtimestamp(t["createdTS"] / 1000)
            new.rdate = datetime.fromtimestamp(t["visibleTS"] / 1000)
            new.id = t['id']

            new.amount = Decimal(str(t["amount"]))

            if "merchantName" in t:
                new.raw = new.label = t["merchantName"]
            elif "partnerName" in t:
                new.raw = CleanText().filter(t["referenceText"]) if "referenceText" in t else CleanText().filter(t["partnerName"])
                new.label = t["partnerName"]
            else:
                new.raw = new.label = ''

            if "originalCurrency" in t:
                new.original_currency = t["originalCurrency"]
            if "originalAmount" in t:
                new.original_amount = Decimal(str(t["originalAmount"]))

            new.type = TYPES.get(t["type"], Transaction.TYPE_UNKNOWN)

            if t["category"] in categories:
                new.category = categories[t["category"]]

            yield new

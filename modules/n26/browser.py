# -*- coding: utf-8 -*-

# Copyright(C) 2016      Benjamin Bouvier
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.

from decimal import Decimal
from datetime import datetime
from functools import wraps

from weboob.browser.browsers import DomainBrowser
from weboob.capabilities.base import find_object, NotAvailable
from weboob.capabilities.bank import Account, Transaction, AccountNotFound
from weboob.browser.filters.standard import CleanText
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser.exceptions import ClientError

# Do not use an APIBrowser since APIBrowser sends all its requests bodies as
# JSON, although N26 only accepts urlencoded format.

def need_login(func):
    @wraps(func)
    def wrapper(browser, *args, **kwargs):
        if browser.auth_method.lower() == 'basic':
            browser.do_login()

        return func(browser, *args, **kwargs)

    return wrapper


class Number26Browser(DomainBrowser):
    BASEURL = 'https://api.tech26.de'

    # Password encoded in base64 for the initial basic-auth scheme used to
    # get an access token.
    INITIAL_TOKEN = 'bXktdHJ1c3RlZC13ZHBDbGllbnQ6c2VjcmV0'

    def request(self, *args, **kwargs):
        """
        Makes it more convenient to add the bearer token and convert the result
        body back to JSON.
        """
        kwargs.setdefault('headers', {})['Authorization'] = self.auth_method + ' ' + self.bearer
        kwargs.setdefault('headers', {})['Accept'] = "application/json"
        return self.open(*args, **kwargs).json()

    def __init__(self, username, password, *args, **kwargs):
        super(Number26Browser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.auth_method = 'Basic'
        self.bearer = Number26Browser.INITIAL_TOKEN

    def do_login(self):
        data = {
            'username': self.username,
            'password': self.password,
            'grant_type': 'password'
        }

        try:
            result = self.request('/oauth/token', data=data, method="POST")
        except ClientError as ex:
            response = ex.response.json()

            if response.get('error') == 'invalid_grant':
                raise BrowserIncorrectPassword(response['error_description'])

            if response.get('title') == 'Error':
                raise BrowserUnavailable(response['message'])

            raise

        self.auth_method = 'bearer'
        self.bearer = result['access_token']

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

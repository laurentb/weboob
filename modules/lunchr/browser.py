# -*- coding: utf-8 -*-

# Copyright(C) 2018      Roger Philibert
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

from weboob.browser.filters.standard import CleanDecimal, CleanText, DateTime
from weboob.browser.filters.json import Dict
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword

from weboob.browser.browsers import APIBrowser
from weboob.capabilities.bank import Account, Transaction


class LunchrBrowser(APIBrowser):
    BASEURL = 'https://api.lunchr.fr'

    def __init__(self, login, password, *args, **kwargs):
        """LunchrBrowser needs login and password to fetch Lunchr API"""
        super(LunchrBrowser, self).__init__(*args, **kwargs)
        # self.session.headers are the HTTP headers for Lunchr API requests
        self.session.headers['x-api-key'] = '644a4ef497286a229aaf8205c2dc12a9086310a8'
        self.session.headers['x-lunchr-app-version'] = 'b6c6ca66c79ca059222779fe8f1ac98c8485b9f0'
        self.session.headers['x-lunchr-platform'] = 'web'
        # self.credentials is the HTTP POST data used in self._auth()
        self.credentials = {
            'user': {
                'email': login,
                'password': password,
            }
        }

    def _auth(self):
        """Authenticate to Lunchr API using self.credentials.
        If authentication succeeds, authorization header is set in self.headers
        and response's json payload is returned unwrapped into dictionary.
        """
        try:
            response = self.open('/api/v0/users/login', data=self.credentials)
        except ClientError as e:
            json = e.response.json()
            if e.response.status_code == 401:
                message = json['result']['error']['message']
                raise BrowserIncorrectPassword(message)
            raise e
        json = Dict('user')(response.json())
        self.session.headers['Authorization'] = 'Bearer ' + Dict('token')(json)
        return json

    def get_account(self, id=None):
        json = self._auth()
        account = Account(id=Dict('id')(json))
        # weboob.capabilities.bank.BaseAccount
        account.bank_name = 'Lunchr'
        account.label = CleanText(Dict('first_name'))(json) + ' ' + CleanText(Dict('last_name'))(json)
        account.currency = CleanText(Dict('meal_voucher_info/balance/currency/iso_3'))(json)
        # weboob.capabilities.bank.Account
        account.type = Account.TYPE_CHECKING
        account.balance = CleanDecimal(Dict('meal_voucher_info/balance/value'))(json)
        account.cardlimit = CleanDecimal(Dict('meal_voucher_info/daily_balance/value'))(json)
        return account

    def iter_accounts(self):
        yield self.get_account()

    def iter_history(self, account):
        page = 0
        while True:
            response = self.open('/api/v0/payments_history?page={:d}'.format(page))
            json = response.json()
            if len(Dict('payments_history')(json)) == 0:
                break
            for payment in Dict('payments_history')(json):
                transaction = Transaction()
                transaction_id = Dict('transaction_number', default=None)(payment)
                # Check if transaction_id is None which indicates failed transaction
                if transaction_id is None:
                    continue
                transaction.id = transaction_id
                transaction.date = DateTime(Dict('executed_at'))(payment)
                transaction.rdate = DateTime(Dict('created_at'))(payment)
                types = {
                    'LUNCHR_CARD_PAYMENT': Transaction.TYPE_CARD,
                    'MEAL_VOUCHER_CREDIT': Transaction.TYPE_DEPOSIT,
                }
                transaction.type = types.get(Dict('type')(payment), Transaction.TYPE_UNKNOWN)
                transaction.label = Dict('name')(payment)
                transaction.amount = CleanDecimal(Dict('amount/value'))(payment)
                yield transaction
            page += 1
            if page >= Dict('pagination/pages_count')(json):
                break

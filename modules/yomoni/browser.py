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

from base64 import b64encode
from functools import wraps
import json
import re

from weboob.browser.browsers import APIBrowser
from weboob.browser.exceptions import ClientError
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable


def need_login(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if self.users is None:
            self.do_login()
        return func(self, *args, **kwargs)

    return wrapper


class YomoniBrowser(APIBrowser):
    BASEURL = 'https://yomoni.fr'

    def __init__(self, username, password, *args, **kwargs):
        super(YomoniBrowser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.users = None
        self.accounts = []
        self.investments = {}
        self.histories = {}
        self.login_headers = {}
        self.request_headers = {}

    def build_request(self, *args, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/vnd.yomoni.v1+json; charset=UTF-8'

        return super(APIBrowser, self).build_request(*args, **kwargs)

    def do_login(self):
        headers_response = self.open('auth/init').headers

        self.login_headers['api_token'] = headers_response['API_TOKEN']
        self.login_headers['csrf'] = headers_response['CSRF']

        self.open('auth/login', method='OPTIONS')

        data = {
            'username': self.username,
            'password': b64encode(self.password.encode('utf8')).decode('ascii').strip(),
        }
        try:
            response = self.open('auth/login', data=data, headers=self.login_headers)
            self.request_headers['api_token'] = response.headers['API_TOKEN']
            self.request_headers['csrf'] = response.headers['CSRF']
            self.users = response.json()
        except ClientError:
            raise BrowserIncorrectPassword()

    waiting_statuses = (
        'RETURN_CUSTOMER_SERVICE', 'SUBSCRIPTION_STEP_2', 'SUBSCRIPTION_STEP_3',
        'SUBSCRIPTION_STEP_4',
    )

    @need_login
    def iter_accounts(self):
        if self.accounts:
            for account in self.accounts:
                yield account
            return

        waiting = False
        for project in self.users['projects']:
            self.open('/user/%s/project/%s/' % (self.users['userId'], project['projectId']), method="OPTIONS")
            me = self.request('/user/%s/project/%s/' % (self.users['userId'], project['projectId']), headers=self.request_headers)

            waiting = (me['status'] in self.waiting_statuses)

            # Check project in progress
            if not me['numeroContrat'] or not me['dateAdhesion']:
                continue

            a = Account()
            a.id = "".join(me['numeroContrat'].split())
            a.label = " ".join(me['supportEpargne'].split("_"))
            a.type = Account.TYPE_LIFE_INSURANCE if "assurance vie" in a.label.lower() else \
                     Account.TYPE_MARKET if "compte titre" in a.label.lower() else \
                     Account.TYPE_PEA if "pea" in a.label.lower() else \
                     Account.TYPE_UNKNOWN
            a.balance = CleanDecimal().filter(me['solde'])
            a.currency = u'EUR' # performanceEuro, montantEuro everywhere in Yomoni JSON
            a.iban = me['ibancompteTitre'] or NotAvailable
            a.number = project['projectId']
            a.valuation_diff = CleanDecimal().filter(me['performanceEuro'])
            a._startbalance = me['montantDepart']

            self.accounts.append(a)

            self.iter_investment(a, me['sousJacents'])

            yield a

        if not self.accounts and waiting:
            raise ActionNeeded("Le service client Yomoni est en attente d'un retour de votre part.")

    @need_login
    def iter_investment(self, account, invs=None):
        if account.id not in self.investments and invs is not None:
            self.investments[account.id] = []
            for inv in invs:
                i = Investment()
                i.label = "%s - %s" % (inv['classification'], inv['description'])
                i.code = inv['isin']
                i.code_type = Investment.CODE_TYPE_ISIN
                i.quantity = CleanDecimal().filter(inv['nombreParts'])
                i.unitprice = CleanDecimal().filter(inv['prixMoyenAchat'])
                i.unitvalue = CleanDecimal().filter(inv['valeurCotation'])
                i.valuation = CleanDecimal().filter(inv['montantEuro'])
                i.vdate = Date().filter(inv['datePosition'])
                # performanceEuro is null sometimes in the JSON we retrieve.
                if inv['performanceEuro']:
                    i.diff = CleanDecimal().filter(inv['performanceEuro'])

                self.investments[account.id].append(i)
        return self.investments[account.id]

    @need_login
    def iter_history(self, account):
        if account.id not in self.histories:
            histories = []
            self.open('/user/%s/project/%s/activity' % (self.users['userId'], account.number), method="OPTIONS")
            for activity in [acc for acc in self.request('/user/%s/project/%s/activity' % (self.users['userId'], account.number), headers=self.request_headers)['activities'] \
                             if acc['details'] is not None]:
                m = re.search(u'([\d\,]+)(?=[\s]+€|[\s]+euro)', activity['details'])
                if "Souscription" not in activity['title'] and not m:
                    continue

                t = Transaction()
                t.label = "%s - %s" % (" ".join(activity['type'].split("_")), activity['title'])
                t.date = Date().filter(activity['date'])
                t.type = Transaction.TYPE_BANK
                amount = account._startbalance if not m else "-%s" % m.group(1) if "FRAIS" in activity['type'] else m.group(1)
                t.amount = CleanDecimal(replace_dots=True).filter(amount)

                histories.append(t)

            self.histories[account.id] = histories
        return self.histories[account.id]

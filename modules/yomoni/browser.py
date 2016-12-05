# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


import json, re

from weboob.browser.browsers import APIBrowser
from weboob.browser.exceptions import ClientError
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.exceptions import BrowserIncorrectPassword
from weboob.capabilities.bank import Account, Investment, Transaction
from weboob.capabilities.base import NotAvailable


class YomoniBrowser(APIBrowser):
    BASEURL = 'https://yomoni.fr'

    def __init__(self, username, password, *args, **kwargs):
        super(YomoniBrowser, self).__init__(*args, **kwargs)
        self.open('auth/init')
        try:
            self.users = self.request('auth/login', data={'username': username, \
                                      'password': password.encode('base64').strip()})
        except ClientError:
            raise BrowserIncorrectPassword
        self.accounts = []
        self.investments = {}
        self.histories = {}

    def build_request(self, *args, **kwargs):
        if 'data' in kwargs:
            kwargs['data'] = json.dumps(kwargs['data'])
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/vnd.yomoni.v1+json; charset=UTF-8'

        return super(APIBrowser, self).build_request(*args, **kwargs)

    def iter_accounts(self):
        if self.accounts:
            for account in self.accounts:
                yield account
            return

        for project in self.users['projects']:
            me = self.request('/user/%s/project/%s/' % (self.users['userId'], project['projectId']))
            # Check project in progress
            if not me['numeroContrat'] or not me['dateAdhesion']:
                continue

            a = Account()
            a.id = "".join(me['numeroContrat'].split())
            a.label = " ".join(me['supportEpargne'].split("_"))
            a.type = Account.TYPE_LIFE_INSURANCE if "assurance vie" in a.label.lower() else \
                     Account.TYPE_MARKET if "compte titre" in a.label.lower() else \
                     Account.TYPE_UNKNOWN
            a.balance = CleanDecimal().filter(me['solde'])
            a.iban = me['ibancompteTitre'] or NotAvailable
            a.number = project['projectId']
            a.valuation_diff = CleanDecimal().filter(me['performanceEuro'])
            a._startbalance = me['montantDepart']

            self.accounts.append(a)

            self.iter_investment(a, me['sousJacents'])

            yield a

    def iter_investment(self, account, invs=None):
        if account not in self.investments and invs is not None:
            self.investments[account] = []
            for inv in invs:
                i = Investment()
                i.label = "%s - %s" % (inv['classification'], inv['description'])
                i.code = inv['isin']
                i.quantity = CleanDecimal().filter(inv['nombreParts'])
                i.unitprice = CleanDecimal().filter(inv['prixMoyenAchat'])
                i.unitvalue = CleanDecimal().filter(inv['valeurCotation'])
                i.valuation = CleanDecimal().filter(inv['montantEuro'])
                i.vdate = Date().filter(inv['datePosition'])
                i.diff = CleanDecimal().filter(inv['performanceEuro'])

                self.investments[account].append(i)
        return self.investments[account]

    def iter_history(self, account):
        if account not in self.histories:
            histories = []
            for activity in [acc for acc in self.request('/user/%s/project/%s/activity' % (self.users['userId'], account.number))['activities'] \
                             if acc['details'] is not None]:
                m = re.search(u'([\d\.]+)(?=[\s]+€|[\s]+euro)', activity['details'])
                if "Souscription" not in activity['title'] and not m:
                    continue

                t = Transaction()
                t.label = "%s - %s" % (" ".join(activity['type'].split("_")), activity['title'])
                t.date = Date().filter(activity['date'])
                t.type = Transaction.TYPE_BANK
                amount = account._startbalance if not m else "-%s" % m.group(1) if "FRAIS" in activity['type'] else m.group(1)
                t.amount = CleanDecimal().filter(amount)

                histories.append(t)

            self.histories[account] = histories
        return self.histories[account]

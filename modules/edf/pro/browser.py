# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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


import json

from datetime import datetime, timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ServerError, ClientError

from .pages import LoginPage, AuthPage, SubscriptionsPage, BillsPage, DocumentsPage


class EdfproBrowser(LoginBrowser):
    BASEURL = 'https://www.edfentreprises.fr'

    login = URL('/openam/json/authenticate', LoginPage)
    auth = URL('/openam/UI/Login.*',
               '/ice/rest/aiguillagemp/redirect', AuthPage)
    contracts = URL('/rest/contratmp/detaillercontrat', SubscriptionsPage)
    bills = URL('/rest/facturemp/getnomtelechargerfacture', BillsPage)
    documents = URL('/rest/facturemp/recherchefacture', DocumentsPage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.cache = {}
        self.cache['docs'] = {}
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfproBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        login_data = self.login.go('/openam/json/authenticate', method='POST').get_json_data(self.username, self.password)
        try:
            self.login.go(data=json.dumps(login_data), headers={'Content-Type': 'application/json'})
        except ClientError as e:
            raise BrowserIncorrectPassword(e.response.json()['message'])

        self.session.cookies['iPlanetDirectoryPro'] = self.page.doc['tokenId']
        self.location(self.absurl('/ice/rest/aiguillagemp/redirect'), allow_redirects=True)

        if self.auth.is_here() and self.page.response.status_code != 303:
            raise BrowserIncorrectPassword

        self.session.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.session.headers['X-XSRF-TOKEN'] = self.session.cookies['XSRF-TOKEN']

    @need_login
    def get_subscription_list(self):
        if "subs" not in self.cache.keys():
            self.contracts.go(data=json.dumps({'listeContrat': [{'refDevis': ''}]}))

            self.cache['subs'] = [s for s in self.page.get_subscriptions()]
        return self.cache['subs']

    @need_login
    def iter_documents(self, subscription):
        if subscription.id not in self.cache['docs']:
            try:
                self.documents.go(data=json.dumps({
                    'dateDebut': (datetime.now() - timedelta(weeks=156)).strftime('%d/%m/%Y'),
                    'dateFin': datetime.now().strftime('%d/%m/%Y'),
                    'element': subscription._refdevis,
                    'typeElementListe': 'CONTRAT'
                }))

                self.cache['docs'][subscription.id] = [d for d in self.page.get_documents()]
            except ServerError:
                self.cache['docs'][subscription.id] = []
        return self.cache['docs'][subscription.id]

    @need_login
    def download_document(self, document):
        if document.url is not NotAvailable:
            try:
                self.bills.go(data=json.dumps({'date': int(document.date.strftime('%s')), \
                                               'iDFelix': document._account_billing, 'numFacture': document._bill_number}))

                return self.open('%s/rest/facturemp/telechargerfichier?fname=%s' % (self.BASEURL, self.page.get_bill_name())).content
            except ServerError:
                return NotAvailable

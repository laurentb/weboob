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

from datetime import datetime

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, AuthPage, SubscriptionsPage, BillsPage, DocumentsPage


class EdfproBrowser(LoginBrowser):
    BASEURL = 'https://www.edfentreprises.fr'

    login = URL('https://www.edf.fr/entreprises', LoginPage)
    auth = URL('/openam/UI/Login',
               '/ice/rest/aiguillagemp/redirect', AuthPage)
    contracts = URL('/rest/contratmp/detaillercontrat', SubscriptionsPage)
    bills = URL('/rest/facturemp/getnomtelechargerfacture', BillsPage)
    documents = URL('/rest/facturemp/recherchefacture', DocumentsPage)

    def do_login(self):
        self.login.go().login(self.username, self.password)
        self.location(self.absurl('/ice/rest/aiguillagemp/redirect'), allow_redirects=False)

        if self.auth.is_here() and self.page.response.status_code != 303:
            raise BrowserIncorrectPassword

        self.session.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.session.headers['X-XSRF-TOKEN'] = self.session.cookies['XSRF-TOKEN']

    @need_login
    def get_subscription_list(self):
        return self.contracts.go(data=json.dumps({'listeContrat': [{'refDevis': ''}]})) \
                             .get_subscriptions()

    @need_login
    def prepare_document_download(self, document):
        return '%s/rest/facturemp/telechargerfichier?fname=%s' % (self.BASEURL, \
                                                                  self.bills.go(data=json.dumps({'date': int(document.date.strftime('%s')), \
                                                                                                 'iDFelix': document._account_billing, \
                                                                                                 'numFacture': document._bill_number})).doc)

    @need_login
    def iter_documents(self, subscription):
        return self.documents.go(data=json.dumps({'dateDebut': '01/01/2013', \
                                           'dateFin': datetime.now().strftime('%d/%m/%Y'), \
                                           'element': subscription.id, \
                                           'typeElementListe': 'CONTRAT'})) \
                             .get_documents()

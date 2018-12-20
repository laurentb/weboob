# -*- coding: utf-8 -*-

# Copyright(C) 2016      Jean Walrave
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

from __future__ import unicode_literals

from datetime import datetime, timedelta

from weboob.browser import LoginBrowser, URL, need_login
from weboob.capabilities.base import NotAvailable
from weboob.exceptions import BrowserIncorrectPassword, ActionNeeded, BrowserUnavailable
from weboob.browser.exceptions import ServerError, ClientError

from .pages import (
    LoginPage, HomePage, AuthPage, ErrorPage, LireSitePage,
    SubscriptionsPage, SubscriptionsAccountPage, BillsPage, DocumentsPage, ProfilePage,
)


class EdfproBrowser(LoginBrowser):
    BASEURL = 'https://www.edfentreprises.fr'

    login = URL('/openam/json/authenticate', LoginPage)
    auth = URL('/openam/UI/Login.*',
               '/ice/rest/aiguillagemp/redirect', AuthPage)
    error = URL(r'/page_erreur/', ErrorPage)
    home = URL('/ice/content/ice-pmse/homepage.html', HomePage)
    liresite = URL(r'/rest/homepagemp/liresite', LireSitePage)
    subscriptions = URL('/rest/homepagemp/lireprofilsfacturation', SubscriptionsPage)
    contracts = URL('/rest/contratmp/consultercontrats', SubscriptionsAccountPage)
    bills = URL('/rest/facturemp/getnomtelechargerfacture', BillsPage)
    documents = URL('/rest/facturemp/recherchefacture', DocumentsPage)
    profile = URL('/rest/servicemp/consulterinterlocuteur', ProfilePage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfproBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.login.go('/openam/json/authenticate', method='POST')
        login_data = self.page.get_data(self.username, self.password)
        try:
            self.login.go(json=login_data)
        except ClientError as e:
            raise BrowserIncorrectPassword(e.response.json()['message'])

        self.session.cookies['ICESSOsession'] = self.page.doc['tokenId']
        self.location(self.absurl('/rest/aiguillagemp/redirect'), allow_redirects=True)

        if self.auth.is_here() and self.page.response.status_code != 303:
            raise BrowserIncorrectPassword()

        if self.error.is_here():
            raise BrowserUnavailable(self.page.get_message())

        self.session.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.session.headers['X-XSRF-TOKEN'] = self.session.cookies['XSRF-TOKEN']

    @need_login
    def get_subscription_list(self):
        self.liresite.go(json={"numPremierSitePage": 0, "pageSize": 100000, "idTdg": None,
                               "critereFiltre": [], "critereTri": []})
        id_site_list = self.page.get_id_site_list()
        if not id_site_list:
            raise ActionNeeded("Vous ne disposez d'aucun contrat actif relatif à vos sites")

        data = {
            'critereFiltre': [],
            'critereTri': [],
            'idTdg': None,
            'pageSize': 100000,
            'startRowNum': 0
        }

        sub_page = self.subscriptions.go(json=data)
        self.contracts.go(json={'refDevisOMList': [], 'refDevisOHList': id_site_list})

        for sub in sub_page.get_subscriptions():
            self.page.update_subscription(sub)
            yield sub

    @need_login
    def iter_documents(self, subscription):
        try:
            self.documents.go(json={
                'dateDebut': (datetime.now() - timedelta(weeks=156)).strftime('%d/%m/%Y'),
                'dateFin': datetime.now().strftime('%d/%m/%Y'),
                'element': subscription._account_id,
                'typeElementListe': 'ID_FELIX'
            })

            return self.page.get_documents()
        except ServerError:
            return []

    @need_login
    def download_document(self, document):
        if document.url is not NotAvailable:
            try:
                self.bills.go(json={'date': int(document.date.strftime('%s')),
                                    'iDFelix': document._account_billing,
                                    'numFacture': document._bill_number})

                return self.open('%s/rest/facturemp/telechargerfichier?fname=%s' % (
                                 self.BASEURL, self.page.get_bill_name())).content
            except ServerError:
                return NotAvailable

    @need_login
    def get_profile(self):
        self.profile.go(json={'idSpcInterlocuteur': ''})

        return self.page.get_profile()

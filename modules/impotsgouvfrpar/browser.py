# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
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


from weboob.browser import AbstractBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginAccessPage, LoginAELPage, ProfilePage, DocumentsPage, BillsPage


class ImpotsParBrowser(AbstractBrowser):
    BASEURL = 'https://cfspart.impots.gouv.fr'
    PARENT = 'franceconnect'

    login_access = URL(r'/LoginAccess', LoginAccessPage)
    login_ael = URL(r'/LoginAEL', LoginAELPage)
    profile = URL(r'/acces-usager/cfs',
                  r'.*/accueilUsager.html', ProfilePage)
    documents = URL(r'.*/documents.html',
                    r'.*/consultation/ConsultationDocument', DocumentsPage)
    bills = URL(r'.*/compteRedirection.html',
                r'.*/consultation/ConsultationDocument',
                r'.*/contrat.html', BillsPage)

    def __init__(self, login_source, *args, **kwargs):
        super(ImpotsParBrowser, self).__init__(*args, **kwargs)
        self.login_source = login_source

    def login_impots(self):
        self.page.login(self.username, self.password)

        msg = self.page.is_login_successful()
        if msg:
            raise BrowserIncorrectPassword(msg)

    def france_connect_do_login(self):
        self.location('https://cfsfc.impots.gouv.fr/', data={'lmAuth': 'FranceConnect'})
        self.fc_call('dgfip', 'https://idp.impots.gouv.fr')
        self.login_impots()
        self.fc_redirect(self.page.get_redirect_url())

    def do_login(self):
        if self.login_source == 'fc':
            self.france_connect_do_login()
            return

        self.login_access.go()
        self.login_impots()

    @need_login
    def iter_subscription(self):
        return self.profile.go().get_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        self.profile.stay_or_go()
        bills_link = self.page.get_bills_link()
        docs_link = self.page.get_documents_link()

        self.location(bills_link)
        self.page.submit_form()
        bills = list()
        for b in self.page.get_bills(subid=subscription.id):
            bills.append(b)

        self.location(docs_link)
        self.page.submit_form()
        documents = list()
        for d in self.page.get_documents(subid=subscription.id):
            # Don't add if it's already a bill : no unique id so...
            label =  d.label.rsplit(' -', 1)[0]
            check = None
            if "-" in label:
                check = len([False for b in bills if label in b.label])
            if not check:
                documents.append(d)
        return iter(bills + documents)

    @need_login
    def get_profile(self):
        self.profile.go()
        return self.page.get_profile()

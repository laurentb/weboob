# -*- coding: utf-8 -*-

# Copyright(C) 2013 Mathieu Jourdan
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

import StringIO
from weboob.deprecated.browser import Browser, BrowserIncorrectPassword
from .pages import LoginPage, HomePage, AccountPage, TimeoutPage, HistoryPage, PdfPage

__all__ = ['GdfSuez']


class GdfSuez(Browser):
    PROTOCOL = 'https'
    DOMAIN = 'www.gdfsuez-dolcevita.fr'
    PAGES = {'.*portail/clients.*?_nfpb=true&_pageLabel=page_identification':  LoginPage,
             '.*portail/clients.*?_nfpb=true&_pageLabel=page_accueil_compte_en_ligne': HomePage,
             '.*p/visualiser_mes_contrats.*?_nfpb=true': AccountPage,
             '.*p/page_historique_de_mes_factures': HistoryPage,
             '.*clients.*?_nfpb=true&_nfls=false&_pageLabel=page_erreur_timeout_session': TimeoutPage
             }

    loginp = '/portailClients/appmanager/portail/clients'
    homep = '/portailClients/appmanager/portail/clients?_nfpb=true&_pageLabel=page_accueil_compte_en_ligne'
    accountp = '/portailClients/client/p/visualiser_mes_contrats?_nfpb=true'
    historyp = '/portailClients/client/p/page_historique_de_mes_factures'

    def __init__(self, *args, **kwargs):
        Browser.__init__(self, *args, **kwargs)

    def home(self):
        self.location(self.homep)

    def is_logged(self):
        if self.is_on_page(LoginPage) or self.is_on_page(TimeoutPage):
            return False
        return True

    def login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        #assert isemail(self.username)
        if not self.is_on_page(LoginPage):
            self.location(self.loginp)
        self.page.login(self.username, self.password)
        if self.is_on_page(LoginPage):
            raise BrowserIncorrectPassword()

    def get_subscription_list(self):
        if not self.is_on_page(AccountPage):
            self.location(self.accountp)
        return self.page.get_subscription_list()

    def get_subscription(self, id):
        assert isinstance(id, basestring)
        for sub in self.get_subscription_list():
            if sub.id == id:
                return sub

    def get_history(self, subscription):
        if not self.is_on_page(HistoryPage):
            self.location(self.historyp)
        return self.page.get_history()

    def get_details(self, subscription):
        bills = self.iter_documents()
        id = bills[0].id
        if not self.is_on_page(HistoryPage):
            self.location(self.historyp)
        url = 'https://www.gdfsuez-dolcevita.fr/' + self.get_document(id)._url
        response = self.openurl(url)
        pdf = PdfPage(StringIO.StringIO(response.read()))
        for detail in pdf.get_details(subscription.label):
            yield detail

    def iter_documents(self):
        if not self.is_on_page(HistoryPage):
            self.location(self.historyp)
        return self.page.get_documents()

    def get_document(self, id):
        assert isinstance(id, basestring)
        for b in self.iter_documents():
            if b.id == id:
                return b

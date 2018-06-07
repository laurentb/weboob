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


from time import time

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, NocaptchaQuestion
from weboob.tools.json import json
from .pages import (
    HomePage, LoginPage, ProfilPage,
    DocumentsPage, WelcomePage, UnLoggedPage, ProfilePage,
)


class EdfBrowser(LoginBrowser):
    BASEURL = 'https://particulier.edf.fr'

    home = URL('/fr/accueil.html', HomePage)
    login = URL('/bin/edf_rc/servlets/authentication', LoginPage)
    not_connected = URL('/fr/accueil/connexion/mon-espace-client.html', UnLoggedPage)
    connected = URL('/fr/accueil/espace-client/tableau-de-bord.html', WelcomePage)
    profil = URL('/services/rest/authenticate/getListContracts', ProfilPage)
    csrf_token = URL('/services/rest/init/initPage\?_=(?P<timestamp>.*)', ProfilPage)
    documents = URL('/services/rest/edoc/getMyDocuments', DocumentsPage)
    bills = URL('/services/rest/edoc/getBillsDocuments', DocumentsPage)
    bill_informations = URL('/services/rest/document/dataUserDocumentGetX', DocumentsPage)
    bill_download = URL('/services/rest/document/getDocumentGetXByData\?csrfToken=(?P<csrf_token>.*)&dn=(?P<dn>.*)&pn=(?P<pn>.*)&di=(?P<di>.*)&bn=(?P<bn>.*)&an=(?P<an>.*)')
    profile = URL('/services/rest/context/getCustomerContext', ProfilePage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.connected.go()
        if self.not_connected.is_here():
            if self.config['captcha_response'].get():
                self.login.go(data={'login': self.username,
                                    'password': self.password,
                                    'rememberMe': "false",
                                    'goto': None,
                                    'gRecaptchaAuthentResponse': self.config['captcha_response'].get()})
                self.connected.go()

                if self.not_connected.is_here():
                    raise BrowserIncorrectPassword()
                else:
                    return

            self.home.go()

            if self.page.has_captcha_request():
                website_key = self.page.get_recaptcha_key()  # google recaptcha plubic key
                website_url = "https://particulier.edf.fr/fr/accueil.html"
                raise NocaptchaQuestion(website_key=website_key, website_url=website_url)
            else:
                raise BrowserIncorrectPassword()
        else:
            return

    def get_csrf_token(self):
        return self.csrf_token.go(timestamp=int(time())).get_token()

    @need_login
    def get_subscription_list(self):
        return self.profil.stay_or_go().iter_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        self.documents.go() # go to docs before, else we get an error, thanks EDF

        return self.bills.go().iter_bills(subid=subscription.id)

    @need_login
    def download_document(self, document):
        token = self.get_csrf_token()

        bills_informations = self.bill_informations.go(headers={'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json, text/plain, */*'}, data=json.dumps({
            'bpNumber': document._bp,
            'csrfToken': token,
            'docId': document._doc_number,
            'docName': 'FACTURE',
            'numAcc': document._num_acc,
            'parNumber': document._par_number
        })).get_bills_informations()

        return self.bill_download.go(csrf_token=token,
                                     dn='FACTURE', pn=document._par_number, \
                                     di=document._doc_number, bn=bills_informations.get('bpNumber'), \
                                     an=bills_informations.get('numAcc')).content

    @need_login
    def get_profile(self):
        self.profile.go()
        return self.page.get_profile()

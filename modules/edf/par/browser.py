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
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword, NocaptchaQuestion
from weboob.tools.decorators import retry
from weboob.tools.json import json
from .pages import (
    HomePage, AuthenticatePage, AuthorizePage, CheckAuthenticatePage, ProfilPage,
    DocumentsPage, WelcomePage, UnLoggedPage, ProfilePage, BillDownload,
)


class BrokenPageError(Exception):
    pass


class EdfBrowser(LoginBrowser):
    BASEURL = 'https://particulier.edf.fr'

    home = URL('/fr/accueil/contrat-et-conso/mon-compte-edf.html', HomePage)
    authenticate = URL(r'https://espace-client.edf.fr/sso/json/authenticate', AuthenticatePage)
    authorize = URL(r'https://espace-client.edf.fr/sso/oauth2/INTERNET/authorize', AuthorizePage)
    check_authenticate = URL('/services/rest/openid/checkAuthenticate', CheckAuthenticatePage)
    not_connected = URL('/fr/accueil/connexion/mon-espace-client.html', UnLoggedPage)
    connected = URL('/fr/accueil/espace-client/tableau-de-bord.html', WelcomePage)
    profil = URL('/services/rest/authenticate/getListContracts', ProfilPage)
    csrf_token = URL(r'/services/rest/init/initPage\?_=(?P<timestamp>.*)', ProfilPage)
    documents = URL('/services/rest/edoc/getMyDocuments', DocumentsPage)
    bills = URL('/services/rest/edoc/getBillsDocuments', DocumentsPage)
    bill_informations = URL('/services/rest/document/dataUserDocumentGetX', DocumentsPage)
    bill_download = URL(r'/services/rest/document/getDocumentGetXByData'
                        r'\?csrfToken=(?P<csrf_token>.*)&dn=(?P<dn>.*)&pn=(?P<pn>.*)'
                        r'&di=(?P<di>.*)&bn=(?P<bn>.*)&an=(?P<an>.*)', BillDownload)
    profile = URL('/services/rest/context/getCustomerContext', ProfilePage)

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.authId = None
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        auth_params = {'realm': '/INTERNET'}
        if self.config['captcha_response'].get() and self.authId:
            self.authenticate.go(method='POST', params=auth_params)
            data = self.page.get_data()
            data['authId'] = self.authId
            data['callbacks'][0]['input'][0]['value'] = self.username
            data['callbacks'][1]['input'][0]['value'] = self.password
            data['callbacks'][2]['input'][0]['value'] = self.config['captcha_response'].get()
            data['callbacks'][3]['input'][0]['value'] = '0'

            try:
                self.authenticate.go(json=data, params=auth_params)
            except ClientError as error:
                resp = error.response
                if resp.status_code == 401:
                    raise BrowserIncorrectPassword(resp.json()['message'])
                raise

            self.session.cookies['ivoiream'] = self.page.get_data()['tokenId']

            # go to this url will auto submit a form which will finalize login
            self.connected.go()

            """
            call check_authenticate url before get subscription in profil, or we'll get an error 'invalid session'
            we do nothing with this response (which contains false btw)
            but edf website expect we call it before or will reject us
            """
            self.check_authenticate.go()
        else:
            self.home.go()
            if self.page.has_captcha_request():
                # google recaptcha site key is returned here, but it's not a good one, take it from another url
                self.authenticate.go(method='POST', params=auth_params)
                data = self.page.get_data()
                website_key = data['callbacks'][4]['output'][0]['value']
                website_url = "https://espace-client.edf.fr/sso/XUI/#login/&realm=%2FINTERNET"
                self.authId = data['authId']

                raise NocaptchaQuestion(website_key=website_key, website_url=website_url)

    def get_csrf_token(self):
        return self.csrf_token.go(timestamp=int(time())).get_token()

    @need_login
    def get_subscription_list(self):
        return self.profil.stay_or_go().iter_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        self.documents.go() # go to docs before, else we get an error, thanks EDF

        return self.bills.go().iter_bills(subid=subscription.id)

    @retry(BrokenPageError, tries=2, delay=4)
    @need_login
    def download_document(self, document):
        token = self.get_csrf_token()

        bills_informations = self.bill_informations.go(headers={
            'Content-Type': 'application/json;charset=UTF-8',
            'Accept': 'application/json, text/plain, */*'},
            data=json.dumps({
            'bpNumber': document._bp,
            'csrfToken': token,
            'docId': document._doc_number,
            'docName': 'FACTURE',
            'numAcc': document._num_acc,
            'parNumber': document._par_number
        })).get_bills_informations()

        self.bill_download.go(csrf_token=token, dn='FACTURE', pn=document._par_number,
                              di=document._doc_number, bn=bills_informations.get('bpNumber'),
                              an=bills_informations.get('numAcc'))

        # sometimes we land to another page that tell us, this document doesn't exist, but just sometimes...
        # make sure this page is the right one to avoid return a html page as document
        if not self.bill_download.is_here():
            raise BrokenPageError()
        return self.page.content

    @need_login
    def get_profile(self):
        self.profile.go()
        return self.page.get_profile()

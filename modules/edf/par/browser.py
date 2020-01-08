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


from time import time

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, BrowserQuestion
from weboob.tools.decorators import retry
from weboob.tools.json import json
from weboob.tools.value import Value
from .pages import (
    HomePage, AuthenticatePage, AuthorizePage, WrongPasswordPage, CheckAuthenticatePage, ProfilPage,
    DocumentsPage, WelcomePage, UnLoggedPage, ProfilePage, BillDownload,
)


class BrokenPageError(Exception):
    pass


class EdfBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://particulier.edf.fr'

    home = URL('/fr/accueil/contrat-et-conso/mon-compte-edf.html', HomePage)
    authenticate = URL(r'https://espace-client.edf.fr/sso/json/authenticate', AuthenticatePage)
    authorize = URL(r'https://espace-client.edf.fr/sso/oauth2/INTERNET/authorize', AuthorizePage)
    wrong_password = URL(r'https://espace-client.edf.fr/connexion/mon-espace-client/templates/openam/authn/PasswordAuth2.html', WrongPasswordPage)
    check_authenticate = URL('/services/rest/openid/checkAuthenticate', CheckAuthenticatePage)
    user_status = URL('/services/rest/checkuserstatus/getUserStatus')
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

    __states__ = ['id_token1', 'otp_data']

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.otp_data = None
        self.id_token1 = None
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(EdfBrowser, self).__init__(*args, **kwargs)

    def locate_browser(self, state):
        pass

    def do_login(self):
        # ********** admire how login works on edf par website **********
        # login part on edf particulier website is very tricky
        # FIRST time we connect we have an otp, BUT not password, we can't know if it is wrong at this moment
        # SECOND time we use password, and not otp
        auth_params = {'realm': '/INTERNET'}

        if self.config['otp'].get():
            self.otp_data['callbacks'][0]['input'][0]['value'] = self.config['otp'].get()
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
            }
            self.authenticate.go(json=self.otp_data, params=auth_params, headers=headers)
            self.id_token1 = self.page.get_data()['callbacks'][1]['output'][0]['value']
            # id_token1 is VERY important, we keep it indefinitely, without it edf will ask again otp
        else:
            self.location('/bin/edf_rc/servlets/sasServlet', params={'processus': 'TDB'})
            if self.connected.is_here():
                # we are already logged
                # sometimes even if password is wrong, you can be logged if you retry
                self.logger.info('already logged')
                return

            self.authenticate.go(method='POST', params=auth_params)
            data = self.page.get_data()
            data['callbacks'][0]['input'][0]['value'] = self.username

            self.authenticate.go(json=data, params=auth_params)
            data = self.page.get_data()  # yes, we have to get response and send it again, beautiful isn't it ?
            if data['stage'] == 'UsernameAuth2':
                # username is wrong
                raise BrowserIncorrectPassword(data['callbacks'][1]['output'][0]['value'])

            if self.id_token1:
                data['callbacks'][0]['input'][0]['value'] = self.id_token1
            else:
                # the FIRST time we connect, we don't have id_token1, we have no choice, we'll receive an otp
                data['callbacks'][0]['input'][0]['value'] = ' '

            self.authenticate.go(json=data, params=auth_params)
            data = self.page.get_data()

            assert data['stage'] in ('HOTPcust3', 'PasswordAuth2'), 'stage is %s' % data['stage']

            if data['stage'] == 'HOTPcust3':  # OTP part
                if self.id_token1:
                    # this shouldn't happen except if id_token1 expire one day, who knows...
                    self.logger.warning('id_token1 is not null but edf ask again for otp')

                # a legend say this url is the answer to life the universe and everything, because it is use EVERYWHERE in login
                self.authenticate.go(json=self.page.get_data(), params=auth_params)
                self.otp_data = self.page.get_data()
                label = self.otp_data['callbacks'][0]['output'][0]['value']
                raise BrowserQuestion(Value('otp', label=label))

            if data['stage'] == 'PasswordAuth2':  # password part
                data['callbacks'][0]['input'][0]['value'] = self.password
                self.authenticate.go(json=self.page.get_data(), params=auth_params)

                # should be SetPasAuth2 if password is ok
                if self.page.get_data()['stage'] == 'PasswordAuth2':
                    attempt_number = self.page.get_data()['callbacks'][1]['output'][0]['value']
                    # attempt_number is the number of wrong password
                    msg = self.wrong_password.go().get_wrongpass_message(attempt_number)
                    raise BrowserIncorrectPassword(msg)

        data = self.page.get_data()
        # yes, send previous data again, i know i know
        self.authenticate.go(json=data, params=auth_params)
        self.session.cookies['ivoiream'] = self.page.get_token()
        self.user_status.go()

        """
        call check_authenticate url before get subscription in profil, or we'll get an error 'invalid session'
        we do nothing with this response (which contains false btw)
        but edf website expect we call it before or will reject us
        """
        self.check_authenticate.go()

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

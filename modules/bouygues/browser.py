# -*- coding: utf-8 -*-

# Copyright(C) 2019      Budget Insight
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

from __future__ import unicode_literals

from time import time
from jose import jwt

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import HTTPNotFound, ClientError
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import urlparse, parse_qsl

from .pages import (
    LoginPage, ForgottenPasswordPage, AppConfigPage, SubscriberPage, SubscriptionPage, SubscriptionDetail, DocumentPage,
    DocumentDownloadPage, DocumentFilePage,
)


class MyURL(URL):
    def go(self, *args, **kwargs):
        kwargs['id_personne'] = self.browser.id_personne
        kwargs['headers'] = self.browser.headers
        return super(MyURL, self).go(*args, **kwargs)


class BouyguesBrowser(LoginBrowser):
    BASEURL = 'https://api.bouyguestelecom.fr'

    login_page = URL(r'https://www.mon-compte.bouyguestelecom.fr/cas/login', LoginPage)
    forgotten_password_page = URL(
            r'https://www.mon-compte.bouyguestelecom.fr/mon-compte/mot-de-passe-oublie',
            r'https://www.bouyguestelecom.fr/mon-compte/mot-de-passe-oublie',
            ForgottenPasswordPage
    )
    app_config = URL(r'https://www.bouyguestelecom.fr/mon-compte/data/app-config.json', AppConfigPage)
    subscriber_page = MyURL(r'/personnes/(?P<id_personne>\d+)$', SubscriberPage)
    subscriptions_page = MyURL(r'/personnes/(?P<id_personne>\d+)/comptes-facturation', SubscriptionPage)
    subscription_detail_page = URL(r'/comptes-facturation/(?P<id_account>\d+)/contrats-payes', SubscriptionDetail)
    document_file_page = URL(r'/comptes-facturation/(?P<id_account>\d+)/factures/.*/documents/.*', DocumentFilePage)
    documents_page = URL(r'/comptes-facturation/(?P<id_account>\d+)/factures(\?|$)', DocumentPage)
    document_download_page = URL(r'/comptes-facturation/(?P<id_account>\d+)/factures/.*(\?|$)', DocumentDownloadPage)

    def __init__(self, username, password, lastname, *args, **kwargs):
        super(BouyguesBrowser, self).__init__(username, password, *args, **kwargs)
        self.lastname = lastname
        self.id_personne = None
        self.headers = None

    def do_login(self):
        self.login_page.go()

        try:
            self.page.login(self.username, self.password, self.lastname)
        except ClientError as e:
            if e.response.status_code == 401:
                raise BrowserIncorrectPassword()
            raise

        if self.login_page.is_here():
            msg = self.page.get_error_message()
            raise BrowserIncorrectPassword(msg)

        if self.forgotten_password_page.is_here():
            # when too much attempt has been done in a short time, bouygues redirect us here,
            # but no message is available on this page
            raise BrowserIncorrectPassword()

        # q is timestamp millisecond
        self.app_config.go(params={'q': int(time()*1000)})
        client_id = self.page.get_client_id()

        params = {
            'client_id': client_id,
            'response_type': 'id_token token',
            'redirect_uri': 'https://www.bouyguestelecom.fr/mon-compte/'
        }
        self.location('https://oauth2.bouyguestelecom.fr/authorize', params=params)
        fragments = dict(parse_qsl(urlparse(self.url).fragment))

        self.id_personne = jwt.get_unverified_claims(fragments['id_token'])['id_personne']
        authorization = 'Bearer ' + fragments['access_token']
        self.headers = {'Authorization': authorization}

    @need_login
    def iter_subscriptions(self):
        subscriber = self.subscriber_page.go().get_subscriber()
        self.subscriptions_page.go()
        for sub in self.page.iter_subscriptions():
            sub.subscriber = subscriber
            sub.label = self.subscription_detail_page.go(id_account=sub.id, headers=self.headers).get_label()
            yield sub

    @need_login
    def iter_documents(self, subscription):
        try:
            self.location(subscription.url, headers=self.headers)
        except HTTPNotFound as error:
            json_response = error.response.json()
            if json_response['error'] in ('facture_introuvable', 'compte_jamais_facture'):
                return []
            raise
        return self.page.iter_documents(subid=subscription.id)

    @need_login
    def download_document(self, document):
        if document.url:
            return self.location(document.url, headers=self.headers).content

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2015 Bezleputh
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

from jose import jwt

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser.exceptions import ClientError
from weboob.tools.compat import urlparse, parse_qs
from .pages import (
    DocumentsPage, HomePage, LoginPage, SubscriberPage, SubscriptionPage, SubscriptionDetailPage,
    SendSMSPage, SendSMSErrorPage, UselessPage, DocumentFilePage
)

from weboob.capabilities.messages import CantSendMessage

__all__ = ['BouyguesBrowser']


class BouyguesBrowser(LoginBrowser):
    BASEURL = 'https://api.bouyguestelecom.fr'
    TIMEOUT = 20

    login = URL('https://www.mon-compte.bouyguestelecom.fr/cas/login', LoginPage)
    home = URL('https://www.bouyguestelecom.fr/mon-compte', HomePage)
    subscriber = URL('/personnes/(?P<idUser>\d+)$', SubscriberPage)
    subscriptions = URL('/personnes/(?P<idUser>\d+)/comptes-facturation', SubscriptionPage)
    subscriptions_details = URL('/comptes-facturation/(?P<idSub>\d+)/contrats-payes', SubscriptionDetailPage)
    document_file = URL('/comptes-facturation/(?P<idSub>\d+)/factures/\d+/documents', DocumentFilePage)
    documents = URL('/comptes-facturation/(?P<idSub>\d+)/factures', DocumentsPage)

    sms_page = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/sendSMS.phtml',
                   'http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/confirmSendSMS.phtml',
                   SendSMSPage)
    confirm = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/resultSendSMS.phtml', UselessPage)
    sms_error_page = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/SMS_erreur.phtml',
                         SendSMSErrorPage)

    def __init__(self, username, password, lastname, *args, **kwargs):
        super(BouyguesBrowser, self).__init__(username, password, *args, **kwargs)
        self.lastname = lastname
        self.headers = None
        self.id_user = None

    def do_login(self):
        self.login.go()

        if self.home.is_here():
            return

        self.page.login(self.username, self.password, self.lastname)

        if not self.home.is_here():
            raise BrowserIncorrectPassword()

        # after login we need to get some tokens to use bouygues api
        data = {
            'response_type': 'id_token token',
            'client_id': 'a360.bouyguestelecom.fr',
            'redirect_uri': 'https://www.bouyguestelecom.fr/mon-compte/'
        }
        self.location('https://oauth2.bouyguestelecom.fr/authorize', params=data)

        parsed_url = urlparse(self.response.url)
        fragment = parse_qs(parsed_url.fragment)

        if not fragment:
            query = parse_qs(parsed_url.query)
            if 'server_error' in query.get('error', []):
                raise BrowserUnavailable(query['error_description'][0])

        claims = jwt.get_unverified_claims(fragment['id_token'][0])
        self.headers = {'Authorization': 'Bearer %s' % fragment['access_token'][0]}
        self.id_user = claims['id_personne']

    @need_login
    def post_message(self, message):
        self.sms_page.go()

        if self.sms_error_page.is_here():
            raise CantSendMessage(self.page.get_error_message())

        receivers = ";".join(list(message.receivers)) if message.receivers else self.username
        self.page.send_sms(message, receivers)

        if self.sms_error_page.is_here():
            raise CantSendMessage(self.page.get_error_message())

        self.confirm.open()

    @need_login
    def iter_subscriptions(self):
        self.subscriber.go(idUser=self.id_user, headers=self.headers)
        subscriber = self.page.get_subscriber()
        phone_list = self.page.get_phone_list()

        self.subscriptions.go(idUser=self.id_user, headers=self.headers)
        for sub in self.page.iter_subscriptions(subscriber=subscriber):
            try:
                self.subscriptions_details.go(idSub=sub.id, headers=self.headers)
                sub.label = self.page.get_label()
            except ClientError:
                # if another person pay for your subscription you may not have access to this page with your credentials
                sub.label = phone_list
            yield sub

    @need_login
    def iter_documents(self, subscription):
        self.location(subscription.url, headers=self.headers)
        return self.page.iter_documents(subid=subscription.id)

    @need_login
    def download_document(self, document):
        self.location(document.url, headers=self.headers)
        return self.open(self.page.get_one_shot_download_url()).content

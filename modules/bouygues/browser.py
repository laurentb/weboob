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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ServerError
from weboob.exceptions import BrowserIncorrectPassword
from .pages import DocumentsPage, HomePage, LoginPage, ProfilePage, SendSMSPage, SendSMSErrorPage

from weboob.capabilities.messages import CantSendMessage

__all__ = ['BouyguesBrowser']


class BouyguesBrowser(LoginBrowser):
    BASEURL = 'https://www.mon-compte.bouyguestelecom.fr/'
    TIMEOUT = 20

    login = URL('cas/login', LoginPage)
    home = URL('https://www.bouyguestelecom.fr/mon-compte', HomePage)
    profile = URL('https://api-mc.bouyguestelecom.fr/client/me/header.json', ProfilePage)
    documents = URL('http://www.bouyguestelecom.fr/parcours/mes-factures/historique\?no_reference=(?P<ref>)', DocumentsPage)

    sms_page = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/sendSMS.phtml',
                   'http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/confirmSendSMS.phtml',
                   SendSMSPage)
    confirm = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/resultSendSMS.phtml')
    sms_error_page = URL('http://www.mobile.service.bbox.bouyguestelecom.fr/services/SMSIHD/SMS_erreur.phtml',
                         SendSMSErrorPage)

    logged = False

    def do_login(self):
        if self.logged:
            return

        self.login.go()

        if self.home.is_here():
            return

        self.page.login(self.username, self.password)

        if not self.home.is_here():
            raise BrowserIncorrectPassword

        self.logged = True
        self.page.logged = True

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
    def get_subscription_list(self):
        try:
            # Informations are available in the header.json file.
            # The only required field is the contract number
            # which is available in the source of the homepage too.
            # Possibly the json file contains more informations but
            # it appears to be unavailable sometimes.
            return self.profile.stay_or_go().get_list()
        except ServerError:
            return self.home.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        self.subid = subscription.id
        return self.documents.stay_or_go(ref=subscription._contract).get_documents()

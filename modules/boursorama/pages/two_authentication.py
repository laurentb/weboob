# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gabriel Serme
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

import re
import urllib2

from weboob.exceptions import BrowserQuestion
from weboob.deprecated.browser import Page, BrowserIncorrectPassword
from weboob.tools.value import Value


class BrowserAuthenticationCodeMaxLimit(BrowserIncorrectPassword):
    pass


class AuthenticationPage(Page):
    MAX_LIMIT = r"vous avez atteint le nombre maximum "\
        "d'utilisation de l'authentification forte."
    SECURE_PAGE = "https://www.boursorama.com/comptes/connexion/securisation/index.phtml"
    REFERER = SECURE_PAGE

    headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows "
                             "NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"
                             " GTB7.1 (.NET CLR 3.5.30729)",
               "Referer": REFERER,
              }

    headers_ajax = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows "
                                  "NT 5.1; en-US; rv:1.9.2.8) Gecko/20100722 Firefox/3.6.8"
                                  " GTB7.1 (.NET CLR 3.5.30729)",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest",
                    "X-Request": "JSON",
                    "X-Brs-Xhr-Request": "true",
                    "X-Brs-Xhr-Schema": "DATA+OUT",
                    "Referer": REFERER,
                   }

    def on_loaded(self):
        pass

    @classmethod
    def authenticate(cls, browser):
        browser.logger.info('Using the PIN Code %s to login', browser.auth_token)
        url = "https://" + browser.DOMAIN + "/ajax/banque/otp.phtml"
        data = "authentificationforteToken=%s&authentificationforteStep=otp&alertType=10100&org=%s&otp=%s&validate=" % (browser.auth_token, cls.REFERER, browser.config['pin_code'].get())
        req = urllib2.Request(url, data, cls.headers_ajax)
        browser.open(req)

        url = "%s?" % (cls.SECURE_PAGE)
        data = "org=/&device=%s" % (browser.config['device'].get())
        req = urllib2.Request(url, data, headers=cls.headers)
        browser.open(req)
        browser.auth_token = None

    def send_sms(self):
        """This function simulates the registration of a device on
        boursorama two factor authentification web page.
        I
        @param device device name to register
        @exception BrowserAuthenticationCodeMaxLimit when daily limit is consumed
        """
        url = "https://%s/ajax/banque/otp.phtml?org=%s&alertType=10100" % (self.browser.DOMAIN, self.REFERER)
        req = urllib2.Request(url, headers=self.headers_ajax)
        response = self.browser.open(req)
        #extrat authentication token from response (in form)
        info = response.read()

        regex = re.compile(self.MAX_LIMIT)
        r = regex.search(info)
        if r:
            raise BrowserAuthenticationCodeMaxLimit("Vous avez atteint le nombre maximum d'utilisation de l'authentification forte")

        regex = re.compile(r"name=\\\"authentificationforteToken\\\" "
            r"value=\\\"(?P<value>\w*?)\\\"")
        r = regex.search(info)
        self.browser.auth_token = r.group('value')

        #step2
        url = "https://" + self.browser.DOMAIN + "/ajax/banque/otp.phtml"
        data = "authentificationforteToken=%s&authentificationforteStep=start&alertType=10100&org=%s&validate=" % (self.browser.auth_token, self.REFERER)
        req = urllib2.Request(url, data, self.headers_ajax)
        response = self.browser.open(req)
        raise BrowserQuestion(Value('pin_code', label='Enter the PIN Code'))

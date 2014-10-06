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

from weboob.deprecated.browser import Page, BrowserIncorrectPassword
import urllib2
import re


class BrowserAuthenticationCodeMaxLimit(BrowserIncorrectPassword):
    pass


class AuthenticationPage(Page):
    MAX_LIMIT = "vous avez atteint le nombre maximum "\
        "d'utilisation de l'authentification forte."

    def on_loaded(self):
        pass

    def authenticate(self, device):
        """This function simulates the registration of a device on
        boursorama two factor authentification web page.
        I
        @param device device name to register
        @exception BrowserAuthenticationCodeMaxLimit when daily limit is consumed
        @exception BrowserIncorrectAuthenticationCode when code is not correct
        """
        DOMAIN = self.browser.DOMAIN
        SECURE_PAGE = "https://www.boursorama.com/comptes/connexion/securisation/index.phtml"
        REFERER = SECURE_PAGE

        #print "Need to authenticate for device", device
        #print "Domain information", DOMAIN

        url = "https://%s/ajax/banque/otp.phtml?org=%s&alertType=10100" % (DOMAIN, REFERER)
        #print url
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

        req = urllib2.Request(url, headers=headers_ajax)
        response = self.browser.open(req)
        #extrat authentication token from response (in form)
        info = response.read()

        regex = re.compile(r"vous avez atteint le nombre maximum d'utilisation de l'authentification forte.")
        r = regex.search(info)
        if r:
            self.logger.info("Boursorama - Vous avez atteint le nombre maximum d'utilisation de l'authentification forte")
            raise BrowserAuthenticationCodeMaxLimit()

        #print "Response from initial request,", len(info), response.info()
        regex = re.compile(r"name=\\\"authentificationforteToken\\\" "
            r"value=\\\"(?P<value>\w*?)\\\"")
        r = regex.search(info)
        token = r.group('value')
        #print "Extracted token", token

        #step2
        url = "https://" + DOMAIN + "/ajax/banque/otp.phtml"
        data = "authentificationforteToken=%s&authentificationforteStep=start&alertType=10100&org=%s&validate=" % (token, REFERER)
        req = urllib2.Request(url, data, headers_ajax)
        response = self.browser.open(req)
        #info = response.read()
        #print "after asking to send token authentification" \
        #   ,len(info), response.info()


        pin = raw_input('Enter the "Boursorama Banque" access code:')
        #print "Pin access code: ''%s''" % (pin)
        url = "https://" + DOMAIN + "/ajax/banque/otp.phtml"
        data = "authentificationforteToken=%s&authentificationforteStep=otp&alertType=10100&org=%s&otp=%s&validate=" % (token, REFERER, pin)
        req = urllib2.Request(url, data, headers_ajax)
        response = self.browser.open(req)
        #info = response.read()
        #print "after pin authentification", len(info), response.info()

        url = "%s?" % (SECURE_PAGE)
        data = "org=/&device=%s" % (device)
        req = urllib2.Request(url, data, headers=headers)
        response = self.browser.open(req)

        #result =        response.read()
        #print response, "\n", response.info()

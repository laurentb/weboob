# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Romain Bignon
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

from selenium.common.exceptions import (
    TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, BrowserHTTPError
from weboob.browser.selenium import (SeleniumBrowser, VisibleXPath)
from weboob.browser import URL

from .pages.login import (
    LoginPage
)

class LoginBrowser(SeleniumBrowser):
    BASEURL = 'https://www.hsbc.com.hk/'

    app_gone = False

    preconnection =      URL(r'https://www.ebanking.hsbc.com.hk/1/2/logon?LANGTAG=en&COUNTRYTAG=US', LoginPage)
    login =           URL(r'https://www.security.online-banking.hsbc.com.hk/gsa/SaaS30Resource/*', LoginPage)

    def __init__(self, username, password, secret, *args, **kwargs):
        super(LoginBrowser, self).__init__(*args, **kwargs)
        self.username = username
        self.password = password
        self.secret = secret
        self.web_space = None
        self.home_url = None

    def _build_capabilities(self):
        capa = super(LoginBrowser, self)._build_capabilities()
        capa['marionette'] = True
        return capa

    def load_state(self, state):
        return

    def do_login(self):

        self.app_gone = False
        self.preconnection.go()
        try:
            self.wait_until(VisibleXPath('//h2[text()[contains(.,"Log on to Internet Banking")]]'), timeout=20)
            self.page.login(self.username)
            self.wait_until_is_here(self.login, 10)
            error = self.page.get_error()
            if error:
                raise BrowserIncorrectPassword(error)

            self.page.get_no_secure_key()
            self.wait_until_is_here(self.login, 10)
            error = self.page.get_error()
            if error:
                raise BrowserHTTPError(error)
            self.page.login_w_secure(self.password, self.secret)
            if self.login.is_here():
                error = self.page.get_error()
                if error:
                    raise BrowserIncorrectPassword(error)
            WebDriverWait(self.driver, 20).until(EC.title_contains("My banking"))

        except TimeoutException as e:
            self.logger.exception("timeout while login")
            raise BrowserUnavailable(e.msg)

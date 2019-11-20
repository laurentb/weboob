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

import os

try:
    from selenium import webdriver
except ImportError:
    raise ImportError('Please install python-selenium')

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import (
    TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable, BrowserHTTPError
from weboob.browser.selenium import (SeleniumBrowser, DirFirefoxProfile, VisibleXPath)
from weboob.browser import URL

from .pages.login import (
    LoginPage
)

class LoginBrowser(SeleniumBrowser):
    BASEURL = 'https://www.hsbc.com.hk/'

    #DRIVER = webdriver.Remote

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

    def _setup_driver(self):
                proxy = Proxy()
                proxy.proxy_type = ProxyType.DIRECT
                if 'http' in self.proxy:
                    proxy.http_proxy = self.proxy['http']
                if 'https' in self.proxy:
                    proxy.ssl_proxy = self.proxy['https']

                capa = self._build_capabilities()
                proxy.add_to_capabilities(capa)

                options = self._build_options()
                # TODO some browsers don't need headless
                # TODO handle different proxy setting?
                options.set_headless(self.HEADLESS)

                if self.DRIVER is webdriver.Firefox:
                    if self.responses_dirname and not os.path.isdir(self.responses_dirname):
                        os.makedirs(self.responses_dirname)

                    options.profile = DirFirefoxProfile(self.responses_dirname)
                    if self.responses_dirname:
                        capa['profile'] = self.responses_dirname
                    self.driver = self.DRIVER(options=options, capabilities=capa)
                elif self.DRIVER is webdriver.Chrome:
                    self.driver = self.DRIVER(options=options, desired_capabilities=capa)
                elif self.DRIVER is webdriver.PhantomJS:
                    if self.responses_dirname:
                        if not os.path.isdir(self.responses_dirname):
                            os.makedirs(self.responses_dirname)
                        log_path = os.path.join(self.responses_dirname, 'selenium.log')
                    else:
                        log_path = NamedTemporaryFile(prefix='weboob_selenium_', suffix='.log', delete=False).name

                    self.driver = self.DRIVER(desired_capabilities=capa, service_log_path=log_path)
                elif self.DRIVER is webdriver.Remote:
                    # self.HEADLESS = False
                    # for debugging purpose
                    self.driver = webdriver.Remote(
                        command_executor='http://<selenium host>:<selenium port>/wd/hub',
                        desired_capabilities=DesiredCapabilities.FIREFOX)
                else:
                    raise NotImplementedError()

                if self.WINDOW_SIZE:
                    self.driver.set_window_size(*self.WINDOW_SIZE)


    def load_state(self, state):
        return

    def do_login(self):
        self.logger.debug("start do_login")

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

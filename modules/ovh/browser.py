# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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

import time
from requests.exceptions import HTTPError, TooManyRedirects
from datetime import datetime, timedelta

from weboob.browser import LoginBrowser, URL, need_login, StatesMixin
from weboob.exceptions import BrowserIncorrectPassword, BrowserQuestion
from weboob.tools.value import Value

from .pages import LoginPage, ProfilePage, BillsPage


class OvhBrowser(LoginBrowser, StatesMixin):
    BASEURL = 'https://www.ovh.com'

    login = URL(
        r'/auth/',
        r'/manager/web/',
        LoginPage,
    )
    profile = URL(r'/engine/api/me', ProfilePage)
    documents = URL(r'/engine/2api/sws/billing/bills\?count=0&date=(?P<fromDate>.*)&dateTo=(?P<toDate>.*)&offset=0', BillsPage)

    __states__ = ('otp_form', 'otp_url')
    STATE_DURATION = 10

    otp_form = None
    otp_url = None

    def __init__(self, config=None, *args, **kwargs):
        self.config = config
        kwargs['username'] = self.config['login'].get()
        kwargs['password'] = self.config['password'].get()
        super(OvhBrowser, self).__init__(*args, **kwargs)

    def locate_browser(self, state):
        # Add Referer to avoid 401 response code when call url for the second time
        try:
            self.location(state['url'], headers={'Referer': self.absurl('/manager/dedicated/index.html')})
        except (HTTPError, TooManyRedirects):
            pass

    def validate_security_form(self):
        res_form = self.otp_form
        res_form['emailCode'] = self.config['pin_code'].get()

        self.location(self.url, data=res_form)

    def do_login(self):
        if self.config['pin_code'].get():
            self.validate_security_form()

            if not self.page.is_logged():
                raise BrowserIncorrectPassword("Login / Password or authentication pin_code incorrect")
            return

        self.login.go()

        if self.page.is_logged():
            return

        self.page.login(self.username, self.password)

        self.page.check_user_double_auth()

        if self.page.check_website_double_auth():
            self.otp_form = self.page.get_security_form()
            self.otp_url = self.url

            raise BrowserQuestion(Value('pin_code', label=self.page.get_otp_message() or 'Please type the OTP you received'))

        if not self.page.is_logged():
            raise BrowserIncorrectPassword(self.page.get_error_message())

    @need_login
    def get_subscription_list(self):
        self.profile.stay_or_go()
        return self.page.get_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        self.documents.stay_or_go(
            fromDate=(datetime.now() - timedelta(days=2 * 365)).strftime("%Y-%m-%dT00:00:00Z"),
            toDate=time.strftime("%Y-%m-%dT%H:%M:%S.999Z"),
        )
        return self.page.get_documents(subid=subscription.id)

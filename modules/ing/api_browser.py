# -*- coding: utf-8 -*-

# Copyright(C) 2019 Sylvie Ye
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
from __future__ import unicode_literals


from collections import OrderedDict

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword, BrowserUnavailable
from weboob.browser.exceptions import ClientError

from .api import LoginPage
from .web import StopPage, ActionNeededPage

from .browser import IngBrowser


class IngAPIBrowser(LoginBrowser):
    BASEURL = 'https://m.ing.fr'

    # Login
    context = URL(r'/secure/api-v1/session/context')
    login = URL(r'/secure/api-v1/login/cif', LoginPage)
    keypad = URL(r'/secure/api-v1/login/keypad', LoginPage)
    pin_page = URL(r'/secure/api-v1/login/pin', LoginPage)

    # Error on old website
    errorpage = URL(r'https://secure.ing.fr/.*displayCoordonneesCommand.*', StopPage)
    actioneeded = URL(r'https://secure.ing.fr/general\?command=displayTRAlertMessage',
                      r'https://secure.ing.fr/protected/pages/common/eco1/moveMoneyForbidden.jsf', ActionNeededPage)

    def __init__(self, *args, **kwargs):
        self.birthday = kwargs.pop('birthday')
        super(IngAPIBrowser, self).__init__(*args, **kwargs)

        self.old_browser = IngBrowser(*args, **kwargs)

    def do_login(self):
        assert self.password.isdigit()
        assert self.birthday.isdigit()

        # login on new website
        # update cookies
        self.context.go()

        data = OrderedDict([
            ('birthDate', self.birthday),
            ('cif', self.username),
        ])
        self.login.go(json=data)

        data = '{"keyPadSize":{"width":3800,"height":1520},"mode":""}'
        self.keypad.go(data=data, headers={'Content-Type': 'application/json'})

        img = self.open('/secure/api-v1/keypad/newkeypad.png').content
        data = {
            'clickPositions': self.page.get_password_coord(img, self.password)
        }

        try:
            self.pin_page.go(json=data, headers={'Referer': 'https://m.ing.fr/secure/login/pin'})
        except ClientError:
            # handle error later
            pass

        error = self.page.get_error()
        if not self.page.is_logged:
            assert error
            if error[0] == 'AUTHENTICATION.INVALID_PIN_CODE':
                raise BrowserIncorrectPassword(error[1])
            assert error[0] != 'INPUT_INVALID', '%s' % error[1]
            raise BrowserUnavailable(error[1])

        self.auth_token = self.page.response.headers['Ingdf-Auth-Token']
        self.session.headers['Ingdf-Auth-Token'] = self.auth_token
        self.session.cookies['ingdfAuthToken'] = self.auth_token

        # Go on old website because new website is not stable
        self.redirect_to_old_browser()

    def redirect_to_old_browser(self):
        token = self.location(
            'https://m.ing.fr/secure/api-v1/sso/exit?context={"originatingApplication":"SECUREUI"}&targetSystem=INTERNET',
            method='POST'
        ).content
        data = {
            'token': token,
            'next': 'protected/pages/index.jsf',
            'redirectUrl': 'protected/pages/index.jsf',
            'targetApplication': 'INTERNET',
            'accountNumber': 'undefined'
        }
        self.session.cookies['produitsoffres'] = 'comptes'
        self.location('https://secure.ing.fr', data=data, headers={'Referer': 'https://secure.ing.fr'})
        self.old_browser.session.cookies.update(self.session.cookies)

    def deinit(self):
        super(IngAPIBrowser, self).deinit()
        self.old_browser.deinit()

    @need_login
    def get_accounts_list(self):
        return self.old_browser.get_accounts_list()

    @need_login
    def get_account(self, _id):
        raise BrowserUnavailable()

    @need_login
    def get_coming(self, account):
        raise BrowserUnavailable()

    @need_login
    def get_history(self, account):
        raise BrowserUnavailable()

    @need_login
    def iter_recipients(self, account):
        raise BrowserUnavailable()

    @need_login
    def init_transfer(self, account, recipient, transfer):
        raise BrowserUnavailable()

    @need_login
    def execute_transfer(self, transfer):
        raise BrowserUnavailable()

    @need_login
    def get_investments(self, account):
        raise BrowserUnavailable()

    ############# CapDocument #############
    @need_login
    def get_subscriptions(self):
        raise BrowserUnavailable()

    @need_login
    def get_documents(self, subscription):
        raise BrowserUnavailable()

    def download_document(self, bill):
        raise BrowserUnavailable()

    ############# CapProfile #############
    @need_login
    def get_profile(self):
        raise BrowserUnavailable()

# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.browser import LoginBrowser, URL
from weboob.browser.pages import HTMLPage, LoggedPage
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import urlparse, parse_qs


class GoogleLoginPage(LoggedPage, HTMLPage):
    def login(self, login, passwd):
        form = self.get_form('//form[@id="gaia_loginform"]', submit='//input[@id="signIn"]')
        form['Email'] = login
        form['Passwd'] = passwd
        form.submit()


class GoogleBrowser(LoginBrowser):
    BASEURL = 'https://accounts.google.com/'

    code = None
    google_login = URL('https://accounts.google.com/(?P<auth>.+)',
                       'AccountLoginInfo',
                       GoogleLoginPage)

    def __init__(self, username, password, redirect_uri, *args, **kwargs):
        super(GoogleBrowser, self).__init__(username, password, *args, **kwargs)
        self.redirect_uri = redirect_uri

    def do_login(self):
        params = {'response_type': 'code',
                  'client_id': '534890559860-r6gn7e3agcpiriehe63dkeus0tpl5i4i.apps.googleusercontent.com',
                  'redirect_uri': self.redirect_uri}

        queryString = "&".join([key+'='+value for key, value in params.items()])
        self.google_login.go(auth='o/oauth2/auth', params=queryString).login(self.username, self.password)

        if self.google_login.is_here():
            self.page.login(self.username, self.password)

        try:
            self.code = parse_qs(urlparse(self.url).query).get('code')[0]
        except:
            raise BrowserIncorrectPassword()

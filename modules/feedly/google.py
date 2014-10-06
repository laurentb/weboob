# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from urlparse import urlparse, parse_qs

from weboob.browser import LoginBrowser, URL
from weboob.browser.pages import HTMLPage
from weboob.exceptions import BrowserIncorrectPassword


class GoogleLoginPage(HTMLPage):
    def login(self, login, passwd):
        form = self.get_form('//form[@id="gaia_loginform"]')
        form['Email'] = login
        form['Passwd'] = passwd
        form.submit()


class GoogleBrowser(LoginBrowser):
    BASEURL = 'https://accounts.google.com'

    code = None
    google_login = URL('https://accounts.google.com/(?P<auth>.+)', GoogleLoginPage)

    def __init__(self, username, password, redirect_uri, *args, **kwargs):
        super(GoogleBrowser, self).__init__(username, password, *args, **kwargs)
        self.redirect_uri = redirect_uri

    def do_login(self):
        params = {'response_type': 'code',
                  'client_id': '534890559860-r6gn7e3agcpiriehe63dkeus0tpl5i4i.apps.googleusercontent.com',
                  'redirect_uri': self.redirect_uri}

        queryString = "&".join([key+'='+value for key, value in params.items()])
        self.google_login.go(auth='o/oauth2/auth', params=queryString).login(self.username, self.password)

        try:
            self.code = parse_qs(urlparse(self.url).query).get('code')[0]
        except:
            raise BrowserIncorrectPassword()

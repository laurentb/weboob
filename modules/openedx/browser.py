# -*- coding: utf-8 -*-

# Copyright(C) 2016      Simon Lipp
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.pages import RawPage, JsonPage, HTMLPage
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword

class LoginPage(HTMLPage):
    def login(self, username, password):
        try:
            self.browser.login_result.open(data = {
                "email": username,
                "password": password,
                "remember": "false"
            })
        except ClientError as e:
            if e.response.status_code == 403:
                raise BrowserIncorrectPassword()
            else:
                raise

        self.logged = True

class OpenEDXBrowser(LoginBrowser):
    login = URL('/login', LoginPage)
    login_result = URL("/user_api/v1/account/login_session/", RawPage)
    threads = URL(r'/courses/(?P<course>.+)/discussion/forum/\?ajax=1&page=(?P<page>\d+)&sort_key=date&sort_order=desc', JsonPage)
    messages = URL(r'/courses/(?P<course>.+)/discussion/forum/(?P<topic>.+)/threads/(?P<id>.+)\?ajax=1&resp_skip=(?P<skip>\d+)&resp_limit=100', JsonPage)
    thread = URL(r'/courses/(?P<course>.+)/discussion/forum/(?P<topic>.+)/threads/(?P<id>.+)', HTMLPage)

    def __init__(self, url, course, *args, **kwargs):
        self.BASEURL = url
        self.course = course
        LoginBrowser.__init__(self, *args, **kwargs)

    def prepare_request(self, req):
        token = self.session.cookies.get("csrftoken")
        if token:
            req.headers.setdefault("X-CSRFToken", token)
        if self.threads.match(req.url) or self.messages.match(req.url):
            req.headers.setdefault("X-Requested-With", "XMLHttpRequest")
        return LoginBrowser.prepare_request(self, req)

    def do_login(self):
        self.login.stay_or_go()
        self.page.login(self.username, self.password)

    @need_login
    def get_threads(self, page=1):
        return self.threads.open(course = self.course, page = page)

    @need_login
    def get_thread(self, topic, id, skip):
        return self.messages.open(course = self.course,
                topic = topic, id = id, skip = skip)

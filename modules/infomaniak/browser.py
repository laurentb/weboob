# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, SubscriptionsPage, DocumentsPage


class InfomaniakBrowser(LoginBrowser):
    BASEURL = 'https://manager.infomaniak.com'

    login = URL(r'https://login.infomaniak.com/api/login', LoginPage)
    profile = URL(r'/v3/api/profile/me', SubscriptionsPage)
    documents = URL(r'/v3/api/invoicing/(?P<subid>.*)/invoices', DocumentsPage)

    def do_login(self):
        self.login.go(data={'login': self.username, 'password': self.password})

        if not self.page.logged:
            raise BrowserIncorrectPassword()

    @need_login
    def iter_subscription(self):
        self.profile.go()
        return [self.page.get_subscription()]

    @need_login
    def iter_documents(self, subscription):
        params = {
            'ajax': 'true',
            'order_by': 'name',
            'order_for[name]': 'asc',
            'page': '1',
            'per_page': '100'
        }
        self.documents.go(subid=subscription.id, params=params)
        return self.page.iter_documents(subid=subscription.id)

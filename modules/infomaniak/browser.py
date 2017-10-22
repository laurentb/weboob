# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from datetime import date

from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, SubscriptionsPage, DocumentsPage


class InfomaniakBrowser(LoginBrowser):
    BASEURL = 'https://manager.infomaniak.com'

    login = URL(r'https://login.infomaniak.com/api/login', LoginPage)
    profile = URL(r'/v3/api/profile/me', SubscriptionsPage)
    documents = URL(r'/admin/facturation/operations/satable_load.php', DocumentsPage)

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
        for offset in range(0, 400, 20):
            data = {
                'iOffset': offset,
                'iCount': 20,
                'sSort': 'none',
                'iCodeService': '0',
                'dStart_toolbar_select': 'allOperations',
                'dStart': '2000-01-01',
                'dEnd': date.today().strftime('%Y-%m-%d'),
                'cb_collections_card': '1',
                'cb_collections_post': '1',
                'cb_collections_paypal': '1',
                'cb_collections_iban': '1',
                'cb_collections_bvr': '1',
                'cb_collections_prepaid': '1',
                'cb_collections_cash': '1',
            }
            self.documents.go(data=data)
            some = False
            for doc in self.page.iter_documents(subid=subscription.id):
                some = True
                yield doc
            if not some:
                break
        else:
            assert False, 'are there that many bills?'

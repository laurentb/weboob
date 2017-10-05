# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.browser.exceptions import ClientError
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, BillsPage


class LampirisBrowser(LoginBrowser):
    BASEURL = 'https://espaceclient.total-spring.fr/'

    loginpage = URL('/user/login', LoginPage)
    billspage = URL('/factures-et-paiements', BillsPage)
    selectcus = URL('/set_selected_cus')

    def __init__(self, *args, **kwargs):
        self.logged = False
        super(LampirisBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        if self.logged:
            return
        self.loginpage.stay_or_go().do_login(self.username, self.password)

        try:
            self.billspage.go()
            self.logged = True
        except ClientError:
            raise BrowserIncorrectPassword()

    @need_login
    def get_subscriptions(self):
        return self.billspage.go().get_subscriptions()

    @need_login
    def get_documents(self, subscription):
        # Select subscription
        self.selectcus.go(params={'cus': subscription})

        # Then, fetch documents
        return self.billspage.go().get_documents()

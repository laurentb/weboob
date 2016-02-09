# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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



from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import HomePage, BillsPage

class LdlcBrowser(LoginBrowser):
    home = URL('/default.aspx', HomePage)
    bills = URL('/Account/CommandListingPage.aspx', BillsPage)

    def __init__(self, website, *args, **kwargs):
        self.website = website
        if website == 'pro':
            self.BASEURL = 'https://secure.ldlc-pro.com/'
        else:
            self.BASEURL = 'https://secure.ldlc.com/'
        super(LdlcBrowser, self).__init__(*args, **kwargs)


    def do_login(self):
        self.location('/Account/LoginPage.aspx',
                      data={'log' : self.username,
                            'pass': self.password})

        self.home.stay_or_go()
        if not self.home.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_subscription_list(self):
        return self.home.stay_or_go().get_list()

    @need_login
    def iter_documents(self, subscription):
        self.bills.stay_or_go()
        bills = list()
        for value in self.page.get_range():
            if self.website == 'pro':
                event = 'ctl00$cphMainContent$ddlDate'
            else:
                event = 'ctl00$ctl00$cphMainContent$cphMainContent$ddlDate'

            self.bills.go(data={event: value, '__EVENTTARGET': 'ctl00$cphMainContent$ddlDate'})

            for i in self.page.get_documents(subid=subscription.id):
                bills.append(i)
        return bills

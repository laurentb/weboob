# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent Paredes
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
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, HomePage, ParBillsPage, ProBillsPage


class LdlcBrowser(LoginBrowser):
    login = URL(r'/Account/LoginPage.aspx', LoginPage)
    home = URL(r'/$', HomePage)

    def do_login(self):
        self.login.stay_or_go()
        website = 'part' if type(self) == LdlcParBrowser else 'pro'
        self.page.login(self.username, self.password, website)

        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def get_subscription_list(self):
        return self.home.stay_or_go().get_list()


class LdlcParBrowser(LdlcBrowser):
    BASEURL = 'https://secure.ldlc.com'

    bills = URL(r'/Account/CommandListingPage.aspx', ParBillsPage)

    @need_login
    def iter_documents(self, subscription):
        self.bills.stay_or_go()
        for value in self.page.get_range():
            self.bills.go(data={'ctl00$ctl00$cphMainContent$cphMainContent$ddlDate': value, '__EVENTTARGET': 'ctl00$cphMainContent$ddlDate'})

            for bill in self.page.iter_documents(subid=subscription.id):
                yield bill


class LdlcProBrowser(LdlcBrowser):
    BASEURL = 'https://secure.ldlc-pro.com'

    bills = URL(r'/Account/CommandListingPage.aspx', ProBillsPage)

    @need_login
    def iter_documents(self, subscription):
        self.bills.stay_or_go()

        for value in self.page.get_range():
            self.bills.go(data={'ctl00$cphMainContent$ddlDate': value, '__EVENTTARGET': 'ctl00$cphMainContent$ddlDate'})
            view_state = self.page.get_view_state()
            # we need position to download file
            position = 1
            hidden_field = self.page.get_ctl00_actScriptManager_HiddenField()
            for bill in self.page.iter_documents(subid=subscription.id):
                bill._position = position
                bill._view_state = view_state
                bill._hidden_field = hidden_field
                position += 1
                yield bill

    @need_login
    def download_document(self, bill):
        data = {
            '__EVENTARGUMENT': '',
            '__EVENTTARGET': '',
            '__LASTFOCUS': '',
            '__SCROLLPOSITIONX': 0,
            '__SCROLLPOSITIONY': 0,
            '__VIEWSTATE': bill._view_state,
            'ctl00$actScriptManager': '',
            'ctl00$cphMainContent$DetailCommand$hfCommand': '',
            'ctl00$cphMainContent$DetailCommand$txtAltEmail': '',
            'ctl00$cphMainContent$ddlDate': bill.date.year,
            'ctl00$cphMainContent$hfCancelCommandId': '',
            'ctl00$cphMainContent$hfCommandId': '',
            'ctl00$cphMainContent$hfCommandSearch': '',
            'ctl00$cphMainContent$hfOrderTri': 1,
            'ctl00$cphMainContent$hfTypeTri': 1,
            'ctl00$cphMainContent$rptCommand$ctl%s$hlFacture.x' % str(bill._position).zfill(2): '7',
            'ctl00$cphMainContent$rptCommand$ctl%s$hlFacture.y' % str(bill._position).zfill(2): '11',
            'ctl00$cphMainContent$txtCommandSearch': '',
            'ctl00$hfCountries': '',
            'ctl00$ucHeaderControl$ctrlSuggestedProductPopUp$HiddenCommandeSupplementaire': '',
            'ctl00$ucHeaderControl$ctrlSuggestedProductPopUp$hiddenPopUp': '',
            'ctl00$ucHeaderControl$txtSearch': 'Rechercher+...',
            'ctl00_actScriptManager_HiddenField': bill._hidden_field
        }

        return self.open(bill.url, data=data).content

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2014 Florent Fourcot
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
from .pages import HomePage, LoginPage, HistoryPage, DetailsPage

__all__ = ['Freemobile']


class Freemobile(LoginBrowser):
    BASEURL = 'https://mobile.free.fr/moncompte/'

    homepage = URL('index.php\?page=home', HomePage)
    detailspage = URL('index.php\?page=suiviconso', DetailsPage)
    loginpage = URL('index.php', LoginPage)
    historypage = URL('ajax.php\?page=consotel_current_month', HistoryPage)

    def do_login(self):
        assert isinstance(self.username, basestring)
        assert isinstance(self.password, basestring)
        assert self.username.isdigit()

        self.loginpage.stay_or_go().login(self.username, self.password)

        self.homepage.go()
        if self.loginpage.is_here():
            raise BrowserIncorrectPassword()

    @need_login
    def get_subscription_list(self):
        subscriptions = self.homepage.stay_or_go().get_list()

        self.detailspage.go()
        for subscription in subscriptions:
            subscription._virtual = self.page.load_virtual(subscription.id)
            subscription.renewdate = self.page.get_renew_date(subscription)
            yield subscription

    def get_history(self, subscription):
        self.historypage.go(data={'login': subscription._login})
        return sorted([x for x in self.page.get_calls()], key=lambda self: self.datetime, reverse=True)

    def get_details(self, subscription):
        return self.detailspage.stay_or_go().get_details(subscription)

    def iter_documents(self, subscription):
        return self.detailspage.stay_or_go().date_bills(subid=subscription.id)

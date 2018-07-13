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
from weboob.capabilities.messages import CantSendMessage
from weboob.exceptions import BrowserIncorrectPassword
from weboob.tools.compat import basestring
from .pages import HomePage, LoginPage, HistoryPage, DetailsPage, OptionsPage, ProfilePage

__all__ = ['Freemobile']


class Freemobile(LoginBrowser):
    BASEURL = 'https://mobile.free.fr/moncompte/'

    homepage = URL('index.php\?page=home', HomePage)
    detailspage = URL('index.php\?page=suiviconso', DetailsPage)
    optionspage = URL('index.php\?page=options&o=(?P<username>)', OptionsPage)
    profile = URL('index.php\?page=coordonnees', ProfilePage)
    loginpage = URL('index.php', LoginPage)
    historypage = URL('ajax.php\?page=consotel_current_month', HistoryPage)
    sendAPI = URL('https://smsapi.free-mobile.fr/sendmsg\?user=(?P<username>)&pass=(?P<apikey>)&msg=(?P<msg>)')

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
            subscription._login = self.page.get_login(subscription.id)
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

    @need_login
    def post_message(self, message):
        receiver = message.thread.id
        username = [
            subscription._login
            for subscription in self.get_subscription_list()
            if subscription.id.split("@")[0] == receiver
        ]
        if username:
            username = username[0]
        else:
            raise CantSendMessage(
                u'Cannot fetch own number.'
            )

        self.optionspage.go(username=username)

        api_key = self.page.get_api_key()
        if not api_key:
            raise CantSendMessage(
                u'Cannot fetch API key for this account, is option enabled?'
            )

        self.sendAPI.go(
            username=username, apikey=api_key,
            msg=message.content
        )

    @need_login
    def get_profile(self):
        self.profile.go()
        return self.page.get_profile()

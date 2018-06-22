# -*- coding: utf-8 -*-

# Copyright(C) 2012-2020  Budget Insight
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


from weboob.browser import LoginBrowser, URL, need_login
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, HomePage, DocumentsPage, ProfilePage


class FreeBrowser(LoginBrowser):
    BASEURL = 'https://adsl.free.fr'

    login = URL('https://subscribe.free.fr/login/', LoginPage)
    home = URL('/home.pl(?P<urlid>.*)', HomePage)
    documents = URL('/liste-factures.pl(?P<urlid>.*)', DocumentsPage)
    profile = URL('/modif_infoscontact.pl(?P<urlid>.*)', ProfilePage)
    address = URL('/show_adresse.pl(?P<urlid>.*)', ProfilePage)

    def __init__(self, *args, **kwargs):
        LoginBrowser.__init__(self, *args, **kwargs)
        self.urlid = None
        self.status = "active"

    def do_login(self):
        self.login.go()

        self.page.login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword
        elif self.documents.is_here():
            self.email = self.username
            self.status = "inactive"

    @need_login
    def get_subscription_list(self):
        self.urlid = self.page.url.rsplit('.pl', 2)[1]
        if self.status is "inactive":
            return self.documents.stay_or_go(urlid=self.urlid).get_list()
        return self.home.stay_or_go(urlid=self.urlid).get_list()

    @need_login
    def iter_documents(self, subscription):
        return self.documents.stay_or_go(urlid=self.urlid).get_documents(subid=subscription.id)

    @need_login
    def get_profile(self):
        # To be sure to load the urlid
        subscriptions = list(self.get_subscription_list())

        self.profile.go(urlid=self.urlid)
        profile = self.page.get_profile(subscriber=subscriptions[0].subscriber)

        self.address.go(urlid=self.urlid)
        self.page.set_address(profile)

        return profile

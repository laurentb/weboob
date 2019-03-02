# -*- coding: utf-8 -*-

# Copyright(C) 2017      Phyks (Lucas Verney)
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


from weboob.browser import LoginBrowser, need_login, URL
from weboob.exceptions import BrowserIncorrectPassword

from .pages import LoginPage, MonBienPage, MesChargesPage


class MyFonciaBrowser(LoginBrowser):
    BASEURL = 'https://fr.foncia.com'

    login = URL(r'/login', LoginPage)
    monBien = URL(r'/espace-client/espace-de-gestion/mon-bien', MonBienPage)
    mesCharges = URL(r'/espace-client/espace-de-gestion/mes-charges/(?P<subscription>.+)', MesChargesPage)

    def do_login(self):
        self.login.stay_or_go().do_login(self.username, self.password)

        self.monBien.go()
        if self.login.is_here():
            raise BrowserIncorrectPassword

    @need_login
    def get_subscriptions(self):
        return self.monBien.stay_or_go().get_subscriptions()

    @need_login
    def get_documents(self, subscription):
        return self.mesCharges.stay_or_go(subscription=subscription).get_documents()

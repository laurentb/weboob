# -*- coding: utf-8 -*-

# Copyright(C) 2017      P4ncake
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


class CityscootBrowser(LoginBrowser):
    BASEURL = 'https://moncompte.cityscoot.eu'

    login = URL(r'/connexion$', LoginPage)
    subscriptions = URL(r'/profil$', SubscriptionsPage)
    documents = URL(r'/users/load_invoices/0$',
                    r'/Factures/details/\d*$', DocumentsPage)

    def __init__(self, *args, **kwargs):
        super(CityscootBrowser, self).__init__(*args, **kwargs)

        self.subs = None
        self.docs = {}

    def do_login(self):
        self.login.go().login(self.username, self.password)

        if self.login.is_here():
            raise BrowserIncorrectPassword(self.page.get_error())

    @need_login
    def get_subscription_list(self):
        if self.subs is None:
            self.subs = [self.subscriptions.stay_or_go().get_item()]
        return self.subs

    @need_login
    def iter_documents(self, subscription):
        if subscription.id not in self.docs:
            self.docs[subscription.id] = [d for d in self.documents.stay_or_go().iter_documents(subid=subscription.id)]
        return self.docs[subscription.id]

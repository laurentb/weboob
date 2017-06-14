# -*- coding: utf-8 -*-

# Copyright(C) 2017      Théo Dorée
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

from .pages import LoginPage, SubscriptionsPage, DocumentsPage


class MyedenredBrowser(LoginBrowser):
    BASEURL = 'https://www.myedenred.fr'

    login = URL(r'/ctr\?Length=7', LoginPage)
    subscriptions = URL(r'/$', SubscriptionsPage)
    documents = URL('/Card/TransactionSet', DocumentsPage)

    def __init__(self, *args, **kwargs):
        super(MyedenredBrowser, self).__init__(*args, **kwargs)

        self.docs = {}

    def do_login(self):
        self.login.go(data={'Email': self.username, 'Password': self.password, 'RememberMe': 'false',
                            'X-Requested-With': 'XMLHttpRequest', 'ReturnUrl': '/'})

    @need_login
    def get_subscription_list(self):
        return self.subscriptions.stay_or_go().iter_subscriptions()

    @need_login
    def iter_documents(self, subscription):
        documents = self.documents.go(data={'command': 'Charger les 10 transactions suivantes',
                                            'ErfBenId': subscription._product_token,
                                            'ProductCode': subscription._product_type,
                                            'SortBy': 'DateOperation',
                                            'StartDate': '',
                                            'EndDate': '',
                                            'PageNum': 10,
                                            'OperationType': 'Debit',
                                            'failed': 'false',
                                            'X-Requested-With': 'XMLHttpRequest'
                                            })
        if subscription.id not in self.docs:
            self.docs[subscription.id] = [d for d in documents.iter_documents(subid=subscription.id)]
        return self.docs[subscription.id]

# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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

from time import sleep

from dateutil.relativedelta import relativedelta

from weboob.browser import URL
from weboob.browser.browsers import LoginBrowser, need_login
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.exceptions import ClientError

from .pages import SigninPage, UserPage, DocumentsPage


class TrainlineBrowser(LoginBrowser):
    BASEURL = 'https://www.trainline.fr'

    signin = URL(r'/api/v5/account/signin', SigninPage)
    user_page = URL(r'/api/v5/user', UserPage)
    documents_page = URL(r'/api/v5/pnrs', DocumentsPage)

    def __init__(self, login, password, *args, **kwargs):
        super(TrainlineBrowser, self).__init__(login, password, *args, **kwargs)
        self.session.headers['X-Requested-With'] = 'XMLHttpRequest'

    def do_login(self):
        try:
            self.signin.go(data={'email': self.username, 'password': self.password})
        except ClientError as error:
            json_response = error.response.json()
            error_list = json_response.get('errors', {}).get('email', [])
            error_message = error_list[0] if error_list else None
            raise BrowserIncorrectPassword(error_message)

        self.session.headers['Authorization'] = 'Token token="%s"' % self.page.get_token()

    @need_login
    def get_subscription_list(self):
        yield self.user_page.go().get_subscription()

    @need_login
    def iter_documents(self, subscription):
        min_date = None
        docs = {}

        i = 0
        while i < 10:
            params = {'date': min_date.strftime('%Y-%m-01')} if min_date else None
            # date params has a very silly behavior
            # * day seems to be useless, (but we have to put it anyway)
            # * server return last 3 months from date (including month we give)
            #     ex: date = 2019-09-01 => return bills from 2019-07-01 to 2019-09-30
            # * this date range behavior seems to not apply for old bills,
            #     it can happens we get bill for 2017 even if we put date=2019-06-01
            #     it is possible maybe because it's the last ones and server doesn't want to
            new_doc = False
            try:
                self.documents_page.go(params=params)
            except ClientError as error:
                # CAUTION: if we perform too many request we can get a 429 response status code
                if error.response.status_code != 429:
                    raise
                # wait 2 seconds and retry, it should work
                sleep(2)
            for doc in self.page.iter_documents(subid=subscription.id):
                if doc.id not in docs.keys():
                    new_doc = True
                    docs[doc.id] = doc

                if min_date is None or min_date > doc.date:
                    min_date = doc.date
            if not new_doc:
                min_date -= relativedelta(months=3)
            i += 1

        return sorted(docs.values(), key=lambda doc: doc.date, reverse=True)

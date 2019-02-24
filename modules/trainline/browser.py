# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from datetime import datetime
from dateutil.relativedelta import relativedelta

from weboob.browser.browsers import APIBrowser
from weboob.exceptions import BrowserIncorrectPassword
from weboob.browser.filters.standard import CleanDecimal, Date
from weboob.browser.exceptions import ClientError
from weboob.capabilities.bill import DocumentTypes, Bill, Subscription


class TrainlineBrowser(APIBrowser):
    BASEURL = 'https://www.trainline.fr/api/v5/'

    def __init__(self, email, password, *args, **kwargs):
        super(TrainlineBrowser, self).__init__(*args, **kwargs)

        self.session.headers['X-Requested-With'] = 'XMLHttpRequest'

        try:
            me = self.request('account/signin', data={'email': email, 'password': password})
        except ClientError:
            raise BrowserIncorrectPassword

        self.session.headers['Authorization'] = 'Token token="%s"' % me['meta']['token']

    def get_subscription_list(self):
        me = self.request('user')['user']
        sub = Subscription()
        sub.subscriber = '%s %s' % (me['first_name'], me['last_name'])
        sub.id = me['id']
        sub.label = me['email']
        yield sub

    def iter_documents(self, subscription):
        docs, docs_len, check, month_back, date = list(), -1, 0, 6, None
        # First request is known
        bills = self.request('pnrs')
        while check < month_back:
            # If not first
            if docs_len > -1 and date:
                if check > 0:
                    # If nothing, we try 4 weeks back
                    date = (datetime.strptime(date, '%Y-%m-%d') - relativedelta(weeks=4)).strftime('%Y-%m-%d')
                else:
                    # Add 8 weeks to last date to be sure to get all
                    date = (datetime.combine(date, datetime.min.time()) + relativedelta(weeks=8)).strftime('%Y-%m-%d')
                bills = self.request('pnrs?date=%s' % date)

            docs_len = len(docs)
            for proof, pnr, trip in zip(bills['proofs'], bills['pnrs'], bills['trips']):
                # Check if not already in docs list
                for doc in docs:
                    if vars(doc)['id'].split('_', 1)[1] == pnr['id']:
                        break
                else:
                    b = Bill()
                    b.id = '%s_%s' % (subscription.id, pnr['id'])
                    b._url = proof['url']
                    b.date = Date().filter(proof['created_at'])
                    b.format = u"pdf"
                    b.label = u'Trajet du %s' % Date().filter(trip['departure_date'])
                    b.type = DocumentTypes.BILL
                    b.vat = CleanDecimal().filter('0')
                    if pnr['cents']:
                        b.price = CleanDecimal().filter(format(pnr['cents']/float(100), '.2f'))
                    b.currency = pnr['currency']
                    docs.append(b)

            check += 1
            # If a new bill is found, we reset check
            if docs_len < len(docs):
                date = b.date
                check = 0

        return iter(docs)

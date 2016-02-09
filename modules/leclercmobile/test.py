# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013  Fourcot Florent
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


from weboob.tools.test import BackendTest


class LeclercMobileTest(BackendTest):
    MODULE = 'leclercmobile'

    def test_list(self):
        """
        Test listing of subscriptions .
        No support of multi-account on the website, we could assume to
        have only one subscription.
        Check the balance if the subscription is ok.
        """
        subscriptions = list(self.backend.iter_subscription())
        self.assertTrue(len(subscriptions) == 1, msg="Account listing failed")
        self.assertTrue(self.backend.get_balance(subscriptions[0]) > 0,
                        msg="Get balance failed")

    def test_downloadbills(self):
        """
        Iter all bills and try to download it.
        """
        for subscription in self.backend.iter_subscription():
            for bill in self.backend.iter_documents(subscription.id):
                self.backend.download_document(bill.id)

    def test_history(self):
        for subscription in self.backend.iter_subscription():
            self.assertTrue(len(list(self.backend.iter_documents_history(subscription))) > 0)

    def test_details(self):
        for subscription in self.backend.iter_subscription():
            details = list(self.backend.get_details(subscription))
            self.assertTrue(len(details) > 5, msg="Not enough details")
            total = 0
            for d in details:
                total += d.price
            self.assertTrue(total > 0, msg="Parsing of price failed")

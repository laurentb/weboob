# -*- coding: utf-8 -*-

# Copyright(C) 2013-2014 Florent Fourcot
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


from weboob.tools.test import BackendTest


class FreeMobileTest(BackendTest):
    MODULE = 'freemobile'

    def test_details(self):
        for subscription in self.backend.iter_subscription():
            details = list(self.backend.get_details(subscription))
            self.assertTrue(len(details) > 4, msg="Not enough details")

    def test_history(self):
        for subscription in self.backend.iter_subscription():
            self.assertTrue(len(list(self.backend.iter_documents_history(subscription))) > 0)

    def test_downloadbills(self):
        """
        Iter all bills and try to download it.
        """
        for subscription in self.backend.iter_subscription():
            for bill in self.backend.iter_documents(subscription.id):
                self.backend.download_document(bill.id)

    def test_list(self):
        """
        Test listing of subscriptions.
        """
        subscriptions = list(self.backend.iter_subscription())
        self.assertTrue(len(subscriptions) > 0, msg="Account listing failed")

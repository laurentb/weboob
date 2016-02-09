# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon, Florent Fourcot
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
from weboob.capabilities.bank import Account
from datetime import timedelta
import random


class INGTest(BackendTest):
    MODULE = 'ing'

    def test_accounts(self):
        l = list(self.backend.iter_accounts())
        for account in l:
            # Test if get_account works
            _id = self.backend.get_account(account.id)
            self.assertTrue(_id.id == account.id)
            # Methods can use Account objects or id. Try one of them
            id_or_account = random.choice([account, account.id])
            if account.type == Account.TYPE_CHECKING or account.type == Account.TYPE_SAVINGS:
                history = list(self.backend.iter_history(id_or_account))
                self.assertTrue(len(history) > 0)
                date = history.pop(0).date
                for elem in history:
                    self.assertTrue(date + timedelta(days=2) >= elem.date)
                    date = elem.date
                recipients = list(self.backend.iter_transfer_recipients(id_or_account))
                self.assertTrue(len(recipients) > 0)
            elif account.type == Account.TYPE_MARKET:
                invest = list(self.backend.iter_investment(id_or_account))
                self.backend.iter_history(id_or_account)  # can be empty. Only try to call it
                self.assertTrue(len(invest) > 0)

    def test_subscriptions(self):
        l = list(self.backend.iter_subscription())
        for sub in l:
            _id = self.backend.get_subscription(sub.id)
            self.assertTrue(_id.id == sub.id)
            bills = list(self.backend.iter_documents(sub))
            self.assertTrue(len(bills) > 0)
            _id = self.backend.get_document(bills[0].id)
            self.assertTrue(_id.id == bills[0].id)
            self.backend.download_document(bills[0].id)

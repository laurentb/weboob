# -*- coding: utf-8 -*-

# Copyright(C) 2012 Romain Bignon
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

class HSBCTest(BackendTest):
    MODULE = 'hsbc'

    def test_hsbc(self):
        l = list(self.backend.iter_accounts())
        if len(l) > 0:
            a = l[0]
            list(self.backend.iter_history(a))

    def test_investments(self):
        life_insurance_accounts = [account for account in self.backend.iter_accounts() if account.type == Account.TYPE_LIFE_INSURANCE]
        investments = {acc.id: list(self.backend.iter_investment(acc)) for acc in life_insurance_accounts}
        for acc in life_insurance_accounts:
            invs = investments[acc.id]
            self.assertLessEquals(sum([inv.valuation for inv in invs]), acc.balance)

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

from decimal import Decimal

from weboob.tools.test import BackendTest
from weboob.capabilities.base import empty
from weboob.tools.capabilities.bank.test import BankStandardTest


class AvivaTest(BackendTest, BankStandardTest):
    MODULE = 'aviva'

    def test_iter_accounts(self):
        account_list = list(self.backend.iter_accounts())

        # check unicity of the account numbers
        self.assertEqual(
            len(account_list),
            len({account.number for account in account_list})
        )
        # check unicity of the account ids
        self.assertEqual(
            len(account_list),
            len({account.id for account in account_list})
        )

        for account in account_list:
            self.assertTrue(account.label)

    def test_iter_investment(self):
        account_list = list(self.backend.iter_accounts())
        for account in account_list:
            investments = list(self.backend.iter_investment(account))
            self.assertEqual(
                sum([invest.portfolio_share for invest in investments]),
                Decimal('1.00')
            )
            for investment in investments:
                self.assertFalse(empty(investment.vdate))
                self.assertTrue(investment.vdate)

    def test_iter_history(self):
        account_list = list(self.backend.iter_accounts())
        for account in account_list:
            history = list(self.backend.iter_history(account))
            self.assertTrue(
                sum([transaction.value for transaction in history]),
                Decimal('1.00')
            )
            for transaction in history:
                self.assertTrue(transaction.amount)

# -*- coding: utf-8 -*-

# Copyright(C) 2017  Vincent Ardisson
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


from weboob.capabilities.base import empty
from weboob.exceptions import NoAccountsException


__all__ = ('BasicTest',)


class BasicTest(object):
    """Mixin for simple tests on CapBank backends.

    This checks:
    * there are accounts
    * accounts have an id, a label and a balance
    * history is implemented (optional)
    * transactions have a date, a label and an amount
    * investments are implemented (optional)
    * investments have a label and a valuation
    * recipients are implemented (optional)
    * recipients have an id and a label
    """

    allow_notimplemented_history = False
    allow_notimplemented_investments = False
    allow_notimplemented_recipients = False

    def check_history(self, account):
        for tr in self.backend.iter_history(account):
            assert not empty(tr.date)
            assert tr.amount
            assert tr.raw or tr.label

            for inv in (tr.investments or []):
                assert inv.label
                assert inv.valuation

    def check_investments(self, account):
        for inv in self.backend.iter_investment(account):
            assert inv.label
            assert inv.valuation

    def check_recipients(self, account):
        for rcpt in self.backend.iter_transfer_recipients(account):
            assert rcpt.id
            assert rcpt.label

    def check_extra(self, account):
        pass

    def test_basic(self):
        try:
            accounts = list(self.backend.iter_accounts())
        except NoAccountsException:
            return

        assert accounts

        for account in accounts:
            assert account.id
            assert account.label
            assert not empty(account.balance)

            try:
                self.check_history(account)
            except NotImplementedError:
                if not self.allow_notimplemented_history:
                    raise

            try:
                self.check_investments(account)
            except NotImplementedError:
                if not self.allow_notimplemented_investments:
                    raise

            try:
                self.check_recipients(account)
            except NotImplementedError:
                if not self.allow_notimplemented_recipients:
                    raise

            self.check_extra(account)

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
from weboob.capabilities.bank import CapBankTransfer, CapBankWealth, CapBankPockets
from weboob.exceptions import NoAccountsException


__all__ = ('BankStandardTest',)


class BankStandardTest(object):
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
    allow_notimplemented_coming = False
    allow_notimplemented_investments = False
    allow_notimplemented_pockets = False
    allow_notimplemented_recipients = False

    def test_basic(self):
        try:
            accounts = list(self.backend.iter_accounts())
        except NoAccountsException:
            return

        assert accounts

        for account in accounts:
            self.check_account(account)

            try:
                self.check_history(account)
            except NotImplementedError:
                if not self.allow_notimplemented_history:
                    raise

            try:
                self.check_coming(account)
            except NotImplementedError:
                if not self.allow_notimplemented_coming:
                    raise

            try:
                self.check_investments(account)
            except NotImplementedError:
                if not self.allow_notimplemented_investments:
                    raise

            try:
                self.check_pockets(account)
            except NotImplementedError:
                if not self.allow_notimplemented_pockets:
                    raise

            try:
                self.check_recipients(account)
            except NotImplementedError:
                if not self.allow_notimplemented_recipients:
                    raise

    def check_account(self, account):
        assert account.id
        assert account.label
        assert not empty(account.balance)

    def check_history(self, account):
        for tr in self.backend.iter_history(account):
            self.check_transaction(account, tr, False)

    def check_coming(self, account):
        for tr in self.backend.iter_coming(account):
            self.check_transaction(account, tr, True)

    def check_transaction(self, account, tr, coming):
        assert not empty(tr.date)
        assert tr.amount
        assert tr.raw or tr.label
        assert tr.date

        for inv in (tr.investments or []):
            assert inv.label
            assert inv.valuation

    def check_investments(self, account):
        if not isinstance(self.backend, CapBankWealth):
            return
        for inv in self.backend.iter_investment(account):
            self.check_investment(account, inv)

    def check_investment(self, account, inv):
        assert inv.label
        assert inv.valuation

    def check_pockets(self, account):
        if not isinstance(self.backend, CapBankPockets):
            return
        for pocket in self.backend.iter_pocket(account):
            self.check_pocket(account, pocket)

    def check_pocket(self, account, pocket):
        assert pocket.amount
        assert not empty(pocket.label)

    def check_recipients(self, account):
        if not isinstance(self.backend, CapBankTransfer):
            return
        for rcpt in self.backend.iter_transfer_recipients(account):
            self.check_recipient(account, rcpt)

    def check_recipient(self, account, rcpt):
        assert rcpt.id
        assert rcpt.label

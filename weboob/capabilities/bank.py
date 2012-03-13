# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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


from datetime import datetime, date

from .base import CapBaseObject
from .collection import ICapCollection


__all__ = ['Account', 'AccountNotFound', 'TransferError', 'ICapBank', 'Transaction']


class AccountNotFound(Exception):
    def __init__(self, msg=None):
        if msg is None:
            msg = 'Account not found'
        Exception.__init__(self, msg)

class TransferError(Exception):
    pass

class Recipient(CapBaseObject):
    def __init__(self):
        CapBaseObject.__init__(self, 0)
        self.add_field('label', basestring)

class Account(Recipient):
    TYPE_UNKNOWN          = 0
    TYPE_CHECKING         = 1  # Transaction, everyday transactions
    TYPE_SAVINGS          = 2  # Savings/Deposit, can be used for everyday banking
    TYPE_DEPOSIT          = 3  # Term or Fixed Deposit, has time/amount constraints
    TYPE_LOAN             = 4
    TYPE_MARKET           = 5  # Stock market or other variable investments
    TYPE_JOINT            = 6  # Joint account

    def __init__(self):
        Recipient.__init__(self)
        self.add_field('type', int, self.TYPE_UNKNOWN)
        self.add_field('balance', float)
        self.add_field('coming', float)

    def __repr__(self):
        return u"<Account id=%r label=%r>" % (self.id, self.label)


class Transaction(CapBaseObject):
    TYPE_UNKNOWN      = 0
    TYPE_TRANSFER     = 1
    TYPE_ORDER        = 2
    TYPE_CHECK        = 3
    TYPE_DEPOSIT      = 4
    TYPE_PAYBACK      = 5
    TYPE_WITHDRAWAL   = 6
    TYPE_CARD         = 7
    TYPE_LOAN_PAYMENT = 8
    TYPE_BANK         = 9

    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('date', (basestring, datetime, date))
        self.add_field('type', int, self.TYPE_UNKNOWN)
        self.add_field('raw', unicode)
        self.add_field('category', unicode)
        self.add_field('label', unicode)
        self.add_field('amount', float)

    def __repr__(self):
        return "<Transaction date='%s' label='%s' amount=%s>" % (self.date,
            self.label, self.amount)

class Transfer(CapBaseObject):
    def __init__(self, id):
        CapBaseObject.__init__(self, id)
        self.add_field('amount', float)
        self.add_field('date', (basestring, datetime, date))
        self.add_field('origin', (int, long, basestring))
        self.add_field('recipient', (int, long, basestring))

class ICapBank(ICapCollection):
    def iter_resources(self, objs, split_path):
        if Account in objs:
            self._restrict_level(split_path)

            return self.iter_accounts()

    def iter_accounts(self):
        raise NotImplementedError()

    def get_account(self, _id):
        raise NotImplementedError()

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        @param account [Account]
        @return [iter(Transaction)]
        """
        raise NotImplementedError()

    def iter_coming(self, account):
        """
        Iter coming transactions on a specific account.

        @param account [Account]
        @return [iter(Transaction)]
        """
        raise NotImplementedError()

    def iter_transfer_recipients(self, account):
        """
        Iter recipients availables for a transfer from a specific account.

        @param account [Account] account which initiate the transfer
        @return [iter(Recipient)]
        """
        raise NotImplementedError()

    def transfer(self, account, recipient, amount, reason=None):
        """
        Make a transfer from an account to a recipient.

        @param account [Account]  account to take money
        @param recipient [Recipient]  account to send money
        @param amount [float]  amount
        @param reason [str]  reason of transfer
        @return [Transfer]  a Transfer object
        """
        raise NotImplementedError()

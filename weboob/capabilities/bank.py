# -*- coding: utf-8 -*-

# Copyright(C) 2010-2015 Romain Bignon
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


from datetime import date, datetime
from binascii import crc32
import re

from weboob.tools.compat import basestring, long

from .base import BaseObject, Field, StringField, DecimalField, IntField, UserError, Currency, NotAvailable
from .date import DateField
from .collection import CapCollection


__all__ = ['AccountNotFound', 'TransferError', 'Recipient', 'Account', 'Transaction', 'Investment', 'Transfer', 'CapBank']


class AccountNotFound(UserError):
    """
    Raised when an account is not found.
    """

    def __init__(self, msg='Account not found'):
        UserError.__init__(self, msg)


class TransferError(UserError):
    """
    A transfer has failed.
    """


class Recipient(BaseObject, Currency):
    """
    Recipient of a transfer.
    """

    label =     StringField('Name')
    currency =  StringField('Currency', default=None)

    def __init__(self):
        BaseObject.__init__(self, 0)

    @property
    def currency_text(self):
        return Currency.currency2txt(self.currency)


class Account(Recipient):
    """
    Bank account.

    It is a child class of :class:`Recipient`, because an account can be
    a recipient of a transfer.
    """
    TYPE_UNKNOWN          = 0
    TYPE_CHECKING         = 1
    "Transaction, everyday transactions"
    TYPE_SAVINGS          = 2
    "Savings/Deposit, can be used for every banking"
    TYPE_DEPOSIT          = 3
    "Term of Fixed Deposit, has time/amount constraints"
    TYPE_LOAN             = 4
    "Loan account"
    TYPE_MARKET           = 5
    "Stock market or other variable investments"
    TYPE_JOINT            = 6
    "Joint account"
    TYPE_CARD             = 7
    "Card account"
    TYPE_LIFE_INSURANCE   = 8
    "Life insurances"

    type =      IntField('Type of account', default=TYPE_UNKNOWN)
    balance =   DecimalField('Balance on this bank account')
    coming =    DecimalField('Coming balance')

    # card attributes
    paydate =   DateField('For credit cards. When next payment is due.')
    paymin =    DecimalField('For credit cards. Minimal payment due.')
    cardlimit = DecimalField('For credit cards. Credit limit.')

    iban =      StringField('International Bank Account Number')

    @property
    def ban(self):
        """ Bank Account Number part of IBAN"""
        if not self.iban:
            return NotAvailable
        return self.iban[4:]

    def __repr__(self):
        return u"<Account id=%r label=%r>" % (self.id, self.label)


class Transaction(BaseObject):
    """
    Bank transaction.
    """
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
    TYPE_CASH_DEPOSIT = 10

    date =      DateField('Debit date on the bank statement')
    rdate =     DateField('Real date, when the payment has been made; usually extracted from the label or from credit card info')
    vdate =     DateField('Value date, or accounting date; usually for professional accounts')
    type =      IntField('Type of transaction, use TYPE_* constants', default=TYPE_UNKNOWN)
    raw =       StringField('Raw label of the transaction')
    category =  StringField('Category of the transaction')
    label =     StringField('Pretty label')
    amount =    DecimalField('Amount of the transaction')

    card =              StringField('Card number (if any)')
    commission =        DecimalField('Commission part on the transaction (in account currency)')

    # International
    original_amount =   DecimalField('Original amount (in another currency)')
    original_currency = StringField('Currency of the original amount')
    country =           StringField('Country of transaction')

    def __repr__(self):
        return "<Transaction date=%r label=%r amount=%r>" % (self.date, self.label, self.amount)

    def unique_id(self, seen=None, account_id=None):
        """
        Get an unique ID for the transaction based on date, amount and raw.

        :param seen: if given, the method uses this dictionary as a cache to
                     prevent several transactions with the same values to have the same
                     unique ID.
        :type seen: :class:`dict`
        :param account_id: if given, add the account ID in data used to create
                           the unique ID. Can be useful if you want your ID to be unique across
                           several accounts.
        :type account_id: :class:`str`
        :returns: an unique ID encoded in 8 length hexadecimal string (for example ``'a64e1bc9'``)
        :rtype: :class:`str`
        """
        crc = crc32(str(self.date))
        crc = crc32(str(self.amount), crc)
        crc = crc32(re.sub('[ ]+', ' ', self.raw.encode("utf-8")), crc)

        if account_id is not None:
            crc = crc32(str(account_id), crc)

        if seen is not None:
            while crc in seen:
                crc = crc32("*", crc)

            seen.add(crc)

        return "%08x" % (crc & 0xffffffff)


class Investment(BaseObject):
    """
    Investment in a financial market.
    """

    label =       StringField('Label of stocks')
    code =        StringField('Identifier of the stock (ISIN code)')
    description = StringField('Short description of the stock')
    quantity =    DecimalField('Quantity of stocks')
    unitprice =   DecimalField('Buy price of one stock')
    unitvalue =   DecimalField('Current value of one stock')
    valuation =   DecimalField('Total current valuation of the Investment')
    diff =        DecimalField('Difference between the buy cost and the current valuation')


class Transfer(BaseObject):
    """
    Transfer from an account to a recipient.
    """

    amount =    DecimalField('Amount to transfer')
    date =      Field('Date of transfer', basestring, date, datetime)
    origin =    Field('Origin of transfer', int, long, basestring)
    recipient = Field('Recipient', int, long, basestring)
    reason =    StringField('Reason')


class CapBank(CapCollection):
    """
    Capability of bank websites to see accounts and transactions.
    """

    def iter_resources(self, objs, split_path):
        """
        Iter resources.

        Default implementation of this method is to return on top-level
        all accounts (by calling :func:`iter_accounts`).

        :param objs: type of objects to get
        :type objs: tuple[:class:`BaseObject`]
        :param split_path: path to discover
        :type split_path: :class:`list`
        :rtype: iter[:class:`BaseObject`]
        """
        if Account in objs:
            self._restrict_level(split_path)

            return self.iter_accounts()

    def iter_accounts(self):
        """
        Iter accounts.

        :rtype: iter[:class:`Account`]
        """
        raise NotImplementedError()

    def get_account(self, id):
        """
        Get an account from its ID.

        :param id: ID of the account
        :type id: :class:`str`
        :rtype: :class:`Account`
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def iter_history(self, account):
        """
        Iter history of transactions on a specific account.

        :param account: account to get history
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def iter_coming(self, account):
        """
        Iter coming transactions on a specific account.

        :param account: account to get coming transactions
        :type account: :class:`Account`
        :rtype: iter[:class:`Transaction`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def iter_transfer_recipients(self, account):
        """
        Iter recipients availables for a transfer from a specific account.

        :param account: account which initiate the transfer
        :type account: :class:`Account`
        :rtype: iter[:class:`Recipient`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def transfer(self, account, recipient, amount, reason=None):
        """
        Make a transfer from an account to a recipient.

        :param account: account to take money
        :type account: :class:`Account`
        :param recipient: account to send money
        :type recipient: :class:`Recipient`
        :param amount: amount
        :type amount: :class:`decimal.Decimal`
        :param reason: reason of transfer
        :type reason: :class:`unicode`
        :rtype: :class:`Transfer`
        :raises: :class:`AccountNotFound`, :class:`TransferError`
        """
        raise NotImplementedError()

    def iter_investment(self, account):
        """
        Iter investment of a market account

        :param account: account to get investments
        :type account: :class:`Account`
        :rtype: iter[:class:`Investment`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

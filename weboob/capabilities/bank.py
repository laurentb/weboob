# -*- coding: utf-8 -*-

# Copyright(C) 2010-2016 Romain Bignon
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
from unidecode import unidecode

from weboob.capabilities.base import empty, find_object
from weboob.exceptions import BrowserQuestion
from weboob.tools.capabilities.bank.iban import is_iban_valid
from weboob.tools.compat import unicode

from .base import BaseObject, Field, StringField, DecimalField, IntField, \
                  UserError, Currency, NotAvailable
from .date import DateField
from .collection import CapCollection


__all__ = ['AccountNotFound', 'TransferError', 'TransferStep', 'Recipient',
           'Account', 'Transaction', 'Investment', 'Transfer', 'CapBank',
           'CapBankTransfer', 'CapBankTransferAddRecipient',
           'RecipientNotFound', 'AddRecipientError', 'AddRecipientStep',
           'BaseAccount',
          ]


class AccountNotFound(UserError):
    """
    Raised when an account is not found.
    """

    def __init__(self, msg='Account not found'):
        super(AccountNotFound, self).__init__(msg)


class RecipientNotFound(UserError):
    """
    Raised when a recipient is not found.
    """

    def __init__(self, msg='Recipient not found'):
        super(RecipientNotFound, self).__init__(msg)


class TransferError(UserError):
    """
    A transfer has failed.
    """

    code = 'transferError'

    def __init__(self, description=None, message=None):
        """
        :param message: error message from the bank, if any
        """

        super(TransferError, self).__init__(message or description)
        self.message = message
        self.description = description


class TransferBankError(TransferError):
    """The transfer was rejected by the bank with a message."""

    code = 'bankMessage'


class TransferInvalidLabel(TransferError):
    """The transfer label is invalid."""

    code = 'invalidLabel'


class TransferInvalidEmitter(TransferError):
    """The emitter account cannot be used for transfers."""

    code = 'invalidEmitter'


class TransferInvalidRecipient(TransferError):
    """The emitter cannot transfer to this recipient."""

    code = 'invalidRecipient'


class TransferInvalidAmount(TransferError):
    """This amount is not allowed."""

    code = 'invalidAmount'


class TransferInvalidCurrency(TransferInvalidAmount):
    """The transfer currency is invalid."""

    code = 'invalidCurrency'


class TransferInsufficientFunds(TransferInvalidAmount):
    """Not enough funds on emitter account."""

    code = 'insufficientFunds'


class TransferInvalidDate(TransferError):
    """This execution date cannot be used."""

    code = 'invalidDate'


class AddRecipientError(UserError):
    """
    Failed trying to add a recipient.
    """

    code = 'AddRecipientError'

    def __init__(self, description=None, message=None):
        """
        :param message: error message from the bank, if any
        """

        super(AddRecipientError, self).__init__(message or description)
        self.message = message
        self.description = description


class RecipientInvalidIban(AddRecipientError):
    code = 'invalidIban'


class RecipientInvalidLabel(AddRecipientError):
    code = 'invalidLabel'


class BaseAccount(BaseObject, Currency):
    """
    Generic class aiming to be parent of :class:`Recipient` and
    :class:`Account`.
    """
    label =          StringField('Pretty label')
    currency =       StringField('Currency', default=None)
    iban =           StringField('International Bank Account Number')
    bank_name =      StringField('Bank Name')

    def __init__(self, id='0', url=None):
        super(BaseAccount, self).__init__(id, url)

    @property
    def currency_text(self):
        return Currency.currency2txt(self.currency)

    @property
    def ban(self):
        """ Bank Account Number part of IBAN"""
        if not self.iban:
            return NotAvailable
        return self.iban[4:]


class Recipient(BaseAccount):
    """
    Recipient of a transfer.
    """
    enabled_at =     DateField('Date of availability')
    category =       StringField('Recipient category')


class Account(BaseAccount):
    """
    Bank account.
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
    TYPE_PEE              = 9
    "Employee savings PEE"
    TYPE_PERCO            = 10
    "Employee savings PERCO"
    TYPE_ARTICLE_83       = 11
    "Article 83"
    TYPE_RSP              = 12
    "Employee savings RSP"
    TYPE_PEA              = 13
    "Share savings"
    TYPE_CAPITALISATION   = 14
    "Life Insurance capitalisation"
    TYPE_PERP             = 15
    "Retirement savings"
    TYPE_MADELIN          = 16
    "Complementary retirement savings"

    type =      IntField('Type of account', default=TYPE_UNKNOWN)
    balance =   DecimalField('Balance on this bank account')
    coming =    DecimalField('Sum of coming movements')

    # card attributes
    paydate =   DateField('For credit cards. When next payment is due.')
    paymin =    DecimalField('For credit cards. Minimal payment due.')
    cardlimit = DecimalField('For credit cards. Credit limit.')

    number =    StringField('Shown by the bank to identify your account ie XXXXX7489')
    # market and lifeinssurance accounts
    valuation_diff = DecimalField('+/- values total')

    def __repr__(self):
        return "<%s id=%r label=%r>" % (type(self).__name__, self.id, self.label)


class Loan(Account):
    """
    Account type dedicated to loans and credits.
    """

    name = StringField('Person name')
    account_label = StringField('Label of the debited account')
    insurance_label = StringField('Label of the insurance')

    total_amount = DecimalField('Total amount loaned')
    available_amount = DecimalField('Amount available') # only makes sense for revolving credit
    used_amount = DecimalField('Amount already used') # only makes sense for revolving credit

    subscription_date = DateField('Date of subscription of the loan')
    maturity_date = DateField('Estimated end date of the loan')
    duration = IntField('Duration of the loan given in months')
    rate = DecimalField('Monthly rate of the loan')

    nb_payments_left = IntField('Number of payments still due')
    nb_payments_done = IntField('Number of payments already done')
    nb_payments_total = IntField('Number total of payments')

    last_payment_amount = DecimalField('Amount of the last payment done')
    last_payment_date = DateField('Date of the last payment done')
    next_payment_amount = DecimalField('Amount of next payment')
    next_payment_date = DateField('Date of the next payment')


class Transaction(BaseObject):
    """
    Bank transaction.
    """
    TYPE_UNKNOWN       = 0
    TYPE_TRANSFER      = 1
    TYPE_ORDER         = 2
    TYPE_CHECK         = 3
    TYPE_DEPOSIT       = 4
    TYPE_PAYBACK       = 5
    TYPE_WITHDRAWAL    = 6
    TYPE_CARD          = 7
    TYPE_LOAN_PAYMENT  = 8
    TYPE_BANK          = 9
    TYPE_CASH_DEPOSIT  = 10
    TYPE_CARD_SUMMARY  = 11
    TYPE_DEFERRED_CARD = 12

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

    # Financial arbitrations
    investments =       Field('List of investments related to the transaction', list, default=[])

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
        crc = crc32(unicode(self.date).encode('utf-8'))
        crc = crc32(unicode(self.amount).encode('utf-8'), crc)
        if not empty(self.raw):
            label = self.raw
        else:
            label = self.label

        crc = crc32(re.sub('[ ]+', ' ', label).encode("utf-8"), crc)

        if account_id is not None:
            crc = crc32(unicode(account_id).encode('utf-8'), crc)

        if seen is not None:
            while crc in seen:
                crc = crc32(b"*", crc)

            seen.add(crc)

        return "%08x" % (crc & 0xffffffff)


class Investment(BaseObject):
    """
    Investment in a financial market.
    """
    CODE_TYPE_ISIN =     u'ISIN'
    CODE_TYPE_AMF =      u'AMF'

    label =              StringField('Label of stocks')
    code =               StringField('Identifier of the stock')
    code_type =          StringField('Type of stock code (ISIN or AMF)')
    description =        StringField('Short description of the stock')
    quantity =           DecimalField('Quantity of stocks')
    unitprice =          DecimalField('Buy price of one stock')
    unitvalue =          DecimalField('Current value of one stock')
    valuation =          DecimalField('Total current valuation of the Investment')
    vdate     =          DateField('Value date of the valuation amount')
    diff =               DecimalField('Difference between the buy cost and the current valuation')
    diff_percent =       DecimalField('Difference in percentage between the buy cost and the current valuation')
    portfolio_share =    DecimalField('Percentage of the current amount relative to the total')

    # International
    original_currency = StringField('Currency of the original amount')
    original_valuation = DecimalField('Original valuation (in another currency)')
    original_unitvalue = DecimalField('Original unitvalue (in another currency)')
    original_unitprice = DecimalField('Original unitprice (in another currency)')
    original_diff = DecimalField('Original diff (in another currency)')

    def __repr__(self):
        return '<Investment label=%r code=%r valuation=%r>' % (self.label, self.code, self.valuation)


class Pocket(BaseObject):
    """
    Pocket
    """
    CONDITION_UNKNOWN                    = 0
    CONDITION_DATE                       = 1
    CONDITION_AVAILABLE                  = 2
    CONDITION_RETIREMENT                 = 3
    CONDITION_WEDDING                    = 4
    CONDITION_DEATH                      = 5
    CONDITION_INDEBTEDNESS               = 6
    CONDITION_DIVORCE                    = 7
    CONDITION_DISABILITY                 = 8
    CONDITION_BUSINESS_CREATION          = 9
    CONDITION_BREACH_EMPLOYMENT_CONTRACT = 10
    CONDITION_UNLOCKING_EXCEPTIONAL      = 11
    CONDITION_THIRD_CHILD                = 12
    CONDITION_EXPIRATION_UNEMPLOYMENT    = 13
    CONDITION_PURCHASE_APARTMENT         = 14

    label =             StringField('Label of pocket')
    amount =            DecimalField('Amount of the pocket')
    quantity =          DecimalField('Quantity of stocks')
    availability_date = DateField('Availability date of the pocket')
    condition =         IntField('Withdrawal condition of the pocket', default=CONDITION_UNKNOWN)
    investment =        Field('Reference to the investment of the pocket', Investment)


class TransferStep(BrowserQuestion):
    def __init__(self, transfer, *values):
        super(TransferStep, self).__init__(*values)
        self.transfer = transfer


class AddRecipientStep(BrowserQuestion):
    def __init__(self, recipient, *values):
        super(AddRecipientStep, self).__init__(*values)
        self.recipient = recipient


class Transfer(BaseObject, Currency):
    """
    Transfer from an account to a recipient.
    """

    amount =          DecimalField('Amount to transfer')
    currency =        StringField('Currency', default=None)
    fees =            DecimalField('Fees', default=None)

    exec_date =       Field('Date of transfer', date, datetime)

    account_id =      StringField('ID of origin account')
    account_iban =    StringField('International Bank Account Number')
    account_label =   StringField('Label of origin account')
    account_balance = DecimalField('Balance of origin account before transfer')

    recipient_id =    StringField('ID of recipient account')
    recipient_iban =  StringField('International Bank Account Number')
    recipient_label = StringField('Label of recipient account')

    label =           StringField('Reason')


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
        return find_object(self.iter_accounts(), id=id, error=AccountNotFound)

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

    def iter_investment(self, account):
        """
        Iter investment of a market account

        :param account: account to get investments
        :type account: :class:`Account`
        :rtype: iter[:class:`Investment`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def iter_pocket(self, account):
        """
        Iter pocket

        :param account: account to get pockets
        :type account: :class:`Account`
        :rtype: iter[:class:`Pocket`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()


class CapCgp(CapBank):
    """
    Capability of cgp website to see accounts and transactions.
    """


class CapBankTransfer(CapBank):
    def iter_transfer_recipients(self, account):
        """
        Iter recipients availables for a transfer from a specific account.

        :param account: account which initiate the transfer
        :type account: :class:`Account`
        :rtype: iter[:class:`Recipient`]
        :raises: :class:`AccountNotFound`
        """
        raise NotImplementedError()

    def init_transfer(self, transfer, **params):
        """
        Initiate a transfer.

        :param :class:`Transfer`
        :rtype: :class:`Transfer`
        :raises: :class:`TransferError`
        """
        raise NotImplementedError()

    def execute_transfer(self, transfer, **params):
        """
        Execute a transfer.

        :param :class:`Transfer`
        :rtype: :class:`Transfer`
        :raises: :class:`TransferError`
        """
        raise NotImplementedError()

    def transfer(self, transfer, **params):
        """
        Do a transfer from an account to a recipient.

        :param :class:`Transfer`
        :rtype: :class:`Transfer`
        :raises: :class:`TransferError`
        """

        if not transfer.amount or transfer.amount <= 0:
            raise TransferInvalidAmount('amount must be strictly positive')

        t = self.init_transfer(transfer, **params)
        for key, value in t.iter_fields():
            if hasattr(transfer, key) and key != 'id':
                transfer_val = getattr(transfer, key)
                try:
                    if hasattr(self, 'transfer_check_%s' % key):
                        assert getattr(self, 'transfer_check_%s' % key)(transfer_val, value)
                    else:
                        assert transfer_val == value or empty(transfer_val)
                except AssertionError:
                    raise TransferError('%s changed during transfer processing (from %s to %s)' % (key, transfer_val, value))
        return self.execute_transfer(t, **params)

    def transfer_check_label(self, old, new):
        return unidecode(old) == unidecode(new)


class CapBankTransferAddRecipient(CapBankTransfer):
    def new_recipient(self, recipient, **params):
        raise NotImplementedError()

    def add_recipient(self, recipient, **params):
        """
        Add a recipient to the connection.

        :param iban: iban of the new recipient.
        :type iban: :class:`str`
        :param label: label of the new recipient.
        :type label: :class`str`
        :raises: :class:`BrowserQuestion`
        :raises: :class:`AddRecipientError`
        :rtype: :class:`Recipient`
        """
        if not is_iban_valid(recipient.iban):
            raise RecipientInvalidIban('Iban is not valid.')
        if not recipient.label:
            raise RecipientInvalidLabel('Recipient label is mandatory.')
        return self.new_recipient(recipient, **params)

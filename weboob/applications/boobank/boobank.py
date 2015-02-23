# -*- coding: utf-8 -*-

# Copyright(C) 2009-2011  Romain Bignon, Christophe Benz
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

from __future__ import print_function

import datetime
import uuid
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse as parse_date
from decimal import Decimal, InvalidOperation

from weboob.browser.browsers import APIBrowser
from weboob.browser.profiles import Weboob
from weboob.exceptions import BrowserHTTPError
from weboob.capabilities.base import empty
from weboob.capabilities.bank import CapBank, Account, Transaction
from weboob.tools.application.repl import ReplApplication, defaultcount
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Boobank']


class OfxFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount', 'category')
    TYPES_ACCTS = ['', 'CHECKING', 'SAVINGS', 'DEPOSIT', 'LOAN', 'MARKET', 'JOINT', 'CARD']
    TYPES_TRANS = ['', 'DIRECTDEP', 'PAYMENT', 'CHECK', 'DEP', 'OTHER', 'ATM', 'POS', 'INT', 'FEE']
    TYPES_CURRS = ['', 'EUR', 'CHF', 'USD']

    balance = Decimal(0)
    coming = Decimal(0)

    def start_format(self, **kwargs):
        account = kwargs['account']
        self.balance = account.balance
        self.coming = account.coming

        self.output(u'OFXHEADER:100')
        self.output(u'DATA:OFXSGML')
        self.output(u'VERSION:102')
        self.output(u'SECURITY:NONE')
        self.output(u'ENCODING:USASCII')
        self.output(u'CHARSET:1252')
        self.output(u'COMPRESSION:NONE')
        self.output(u'OLDFILEUID:NONE')
        self.output(u'NEWFILEUID:%s\n' % uuid.uuid1())
        self.output(u'<OFX><SIGNONMSGSRSV1><SONRS><STATUS><CODE>0<SEVERITY>INFO</STATUS>')
        self.output(u'<DTSERVER>%s113942<LANGUAGE>ENG</SONRS></SIGNONMSGSRSV1>' % datetime.date.today().strftime('%Y%m%d'))
        self.output(u'<BANKMSGSRSV1><STMTTRNRS><TRNUID>%s' % uuid.uuid1())
        self.output(u'<STATUS><CODE>0<SEVERITY>INFO</STATUS><CLTCOOKIE>null<STMTRS>')
        self.output(u'<CURDEF>%s<BANKACCTFROM>' % (account.currency or 'EUR'))
        self.output(u'<BANKID>null')
        self.output(u'<BRANCHID>null')
        self.output(u'<ACCTID>%s' % account.id)
        try:
            account_type = self.TYPES_ACCTS[account.type]
        except IndexError:
            account_type = ''
        self.output(u'<ACCTTYPE>%s' % (account_type or 'CHECKING'))
        self.output(u'<ACCTKEY>null</BANKACCTFROM>')
        self.output(u'<BANKTRANLIST>')
        self.output(u'<DTSTART>%s' % datetime.date.today().strftime('%Y%m%d'))
        self.output(u'<DTEND>%s' % datetime.date.today().strftime('%Y%m%d'))

    def format_obj(self, obj, alias):
        if obj.type != 0:
            result = u'<STMTTRN><TRNTYPE>%s\n' % self.TYPES_TRANS[obj.type]
        else:
            result = u'<STMTTRN><TRNTYPE>%s\n' % ('DEBIT' if obj.amount < 0 else 'CREDIT')

        result += u'<DTPOSTED>%s\n' % obj.date.strftime('%Y%m%d')
        result += u'<TRNAMT>%s\n' % obj.amount
        result += u'<FITID>%s\n' % obj.unique_id()

        if hasattr(obj, 'label') and not empty(obj.label):
            result += u'<NAME>%s</STMTTRN>' % obj.label.replace('&', '&amp;')
        else:
            result += u'<NAME>%s</STMTTRN>' % obj.raw.replace('&', '&amp;')

        return result

    def flush(self):
        self.output(u'</BANKTRANLIST>')
        self.output(u'<LEDGERBAL><BALAMT>%s' % self.balance)
        self.output(u'<DTASOF>%s</LEDGERBAL>' % datetime.date.today().strftime('%Y%m%d'))

        try:
            self.output(u'<AVAILBAL><BALAMT>%s' % (self.balance + self.coming))
        except TypeError:
            self.output(u'<AVAILBAL><BALAMT>%s' % self.balance)

        self.output(u'<DTASOF>%s</AVAILBAL>' % datetime.date.today().strftime('%Y%m%d'))
        self.output(u'</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>')


class QifFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount')

    def start_format(self, **kwargs):
        self.output(u'!Type:Bank')

    def format_obj(self, obj, alias):
        result = u'D%s\n' % obj.date.strftime('%d/%m/%y')
        result += u'T%s\n' % obj.amount
        if hasattr(obj, 'category') and not empty(obj.category):
            result += u'N%s\n' % obj.category
        result += u'M%s\n' % obj.raw
        result += u'^'
        return result


class PrettyQifFormatter(QifFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount', 'category')

    def start_format(self, **kwargs):
        self.output(u'!Type:Bank')

    def format_obj(self, obj, alias):
        if hasattr(obj, 'rdate') and not empty(obj.rdate):
            result = u'D%s\n' % obj.rdate.strftime('%d/%m/%y')
        else:
            result = u'D%s\n' % obj.date.strftime('%d/%m/%y')
        result += u'T%s\n' % obj.amount

        if hasattr(obj, 'category') and not empty(obj.category):
            result += u'N%s\n' % obj.category

        if hasattr(obj, 'label') and not empty(obj.label):
            result += u'M%s\n' % obj.label
        else:
            result += u'M%s\n' % obj.raw

        result += u'^'
        return result


class TransactionsFormatter(IFormatter):
    MANDATORY_FIELDS = ('date', 'label', 'amount')
    TYPES = ['', 'Transfer', 'Order', 'Check', 'Deposit', 'Payback', 'Withdrawal', 'Card', 'Loan', 'Bank']

    def start_format(self, **kwargs):
        self.output(' Date         Category     Label                                                  Amount ')
        self.output('------------+------------+---------------------------------------------------+-----------')

    def format_obj(self, obj, alias):
        if hasattr(obj, 'category') and obj.category:
            _type = obj.category
        else:
            try:
                _type = self.TYPES[obj.type]
            except (IndexError, AttributeError):
                _type = ''

        label = obj.label
        if not label and hasattr(obj, 'raw'):
            label = obj.raw
        date = obj.date.strftime('%Y-%m-%d') if not empty(obj.date) else ''
        amount = obj.amount or Decimal('0')
        return ' %s   %s %s %s' % (self.colored('%-10s' % date, 'blue'),
                                   self.colored('%-12s' % _type[:12], 'magenta'),
                                   self.colored('%-50s' % label[:50], 'yellow'),
                                   self.colored('%10.2f' % amount, 'green' if amount >= 0 else 'red'))


class TransferFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'origin', 'recipient', 'amount')
    DISPLAYED_FIELDS = ('reason', )

    def format_obj(self, obj, alias):
        result = u'------- Transfer %s -------\n' % obj.fullid
        result += u'Date:       %s\n' % obj.date
        result += u'Origin:     %s\n' % obj.origin
        result += u'Recipient:  %s\n' % obj.recipient
        result += u'Amount:     %.2f\n' % obj.amount
        if obj.reason:
            result += u'Reason:     %s\n' % obj.reason
        return result


class InvestmentFormatter(IFormatter):
    MANDATORY_FIELDS = ('label', 'quantity', 'unitvalue')
    DISPLAYED_FIELDS = ('code', 'diff')

    tot_valuation = Decimal(0)
    tot_diff = Decimal(0)

    def start_format(self, **kwargs):
        self.output(' Label                            Code          Quantity     Unit Value   Valuation    diff    ')
        self.output('-------------------------------+--------------+------------+------------+------------+---------')

    def check_emptyness(self, obj):
        if not empty(obj):
            return (obj, '%11.2f')
        return ('---', '%11s')

    def format_obj(self, obj, alias):
        label = obj.label

        if not empty(obj.diff):
            diff = obj.diff
        elif not empty(obj.quantity) and not empty(obj.unitprice):
            diff = obj.valuation - (obj.quantity * obj.unitprice)
        else:
            diff = '---'
            format_diff = '%8s'
        if isinstance(diff, Decimal):
            format_diff = '%8.2f'
            self.tot_diff += diff

        if not empty(obj.quantity):
            quantity = obj.quantity
            format_quantity = '%11.2f'
            if obj.quantity._isinteger():
                format_quantity = '%11d'
        else:
            format_quantity = '%11s'
            quantity = '---'

        unitvalue, format_unitvalue = self.check_emptyness(obj.unitvalue)
        valuation, format_valuation = self.check_emptyness(obj.valuation)
        if isinstance(valuation, Decimal):
            self.tot_valuation += obj.valuation

        if empty(obj.code) and not empty(obj.description):
            code = obj.description
        else:
            code = obj.code

        return u' %s  %s  %s  %s  %s  %s' % \
               (self.colored('%-30s' % label[:30], 'red'),
                self.colored('%-12s' % code[:12], 'yellow') if not empty(code) else ' ' * 12,
                self.colored(format_quantity % quantity, 'yellow'),
                self.colored(format_unitvalue % unitvalue, 'yellow'),
                self.colored(format_valuation % valuation, 'yellow'),
                self.colored(format_diff % diff, 'green' if diff >= 0 else 'red')
                )

    def flush(self):
        self.output(u'-------------------------------+--------------+------------+------------+------------+---------')
        self.output(u'                                                                  Total  %s %s' %
                    (self.colored('%11.2f' % self.tot_valuation, 'yellow'),
                     self.colored('%9.2f' % self.tot_diff, 'green' if self.tot_diff >= 0 else 'red'))
                    )
        self.tot_valuation = Decimal(0)
        self.tot_diff = Decimal(0)


class RecipientListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'label')

    def start_format(self, **kwargs):
        self.output('Available recipients:')

    def get_title(self, obj):
        return obj.label


class AccountListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'label', 'balance', 'coming')

    tot_balance = Decimal(0)
    tot_coming = Decimal(0)

    def start_format(self, **kwargs):
        self.output('               %s  Account                     Balance    Coming ' % ((' ' * 15) if not self.interactive else ''))
        self.output('------------------------------------------%s+----------+----------' % (('-' * 15) if not self.interactive else ''))

    def format_obj(self, obj, alias):
        if alias is not None:
            id = '%s (%s)' % (self.colored('%3s' % ('#' + alias), 'red', 'bold'),
                              self.colored(obj.backend, 'blue', 'bold'))
            clean = '#%s (%s)' % (alias, obj.backend)
            if len(clean) < 15:
                id += (' ' * (15 - len(clean)))
        else:
            id = self.colored('%30s' % obj.fullid, 'red', 'bold')

        balance = obj.balance or Decimal('0')
        coming = obj.coming or Decimal('0')
        result = u'%s %s %s  %s' % (id,
                                    self.colored('%-25s' % obj.label[:25], 'yellow'),
                                    self.colored('%9.2f' % obj.balance, 'green' if balance >= 0 else 'red') if not empty(obj.balance) else ' ' * 9,
                                    self.colored('%9.2f' % obj.coming, 'green' if coming >= 0 else 'red') if not empty(obj.coming) else '')

        self.tot_balance += balance
        self.tot_coming += coming
        return result

    def flush(self):
        self.output(u'------------------------------------------%s+----------+----------' % (('-' * 15) if not self.interactive else ''))
        self.output(u'%s                                    Total   %s   %s' % (
                    (' ' * 15) if not self.interactive else '',
                    self.colored('%8.2f' % self.tot_balance, 'green' if self.tot_balance >= 0 else 'red'),
                    self.colored('%8.2f' % self.tot_coming, 'green' if self.tot_coming >= 0 else 'red'))
                    )
        self.tot_balance = Decimal(0)
        self.tot_coming = Decimal(0)


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '1.1'
    COPYRIGHT = 'Copyright(C) 2010-YEAR Romain Bignon, Christophe Benz'
    CAPS = CapBank
    DESCRIPTION = "Console application allowing to list your bank accounts and get their balance, " \
                  "display accounts history and coming bank operations, and transfer money from an account to " \
                  "another (if available)."
    SHORT_DESCRIPTION = "manage bank accounts"
    EXTRA_FORMATTERS = {'account_list':   AccountListFormatter,
                        'recipient_list': RecipientListFormatter,
                        'transfer':       TransferFormatter,
                        'qif':            QifFormatter,
                        'pretty_qif':     PrettyQifFormatter,
                        'ofx':            OfxFormatter,
                        'ops_list':       TransactionsFormatter,
                        'investment_list': InvestmentFormatter,
                        }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'ls':          'account_list',
                           'list':        'account_list',
                           'transfer':    'transfer',
                           'history':     'ops_list',
                           'coming':      'ops_list',
                           'investment':  'investment_list',
                           }
    COLLECTION_OBJECTS = (Account, Transaction, )

    def load_default_backends(self):
        self.load_backends(CapBank, storage=self.create_storage())

    def _complete_account(self, exclude=None):
        if exclude:
            exclude = '%s@%s' % self.parse_id(exclude)

        return [s for s in self._complete_object() if s != exclude]

    def do_list(self, line):
        """
        list [-U]

        List accounts.
        Use -U to disable sorting of results.
        """
        return self.do_ls(line)

    def show_history(self, command, line):
        id, end_date = self.parse_command_args(line, 2, 1)

        account = self.get_object(id, 'get_account', [])
        if not account:
            print('Error: account "%s" not found (Hint: try the command "list")' % id, file=self.stderr)
            return 2

        if end_date is not None:
            try:
                end_date = parse_date(end_date)
            except ValueError:
                print('"%s" is an incorrect date format (for example "%s")' %
                      (end_date, (datetime.date.today() - relativedelta(months=1)).strftime('%Y-%m-%d')), file=self.stderr)
                return 3
            old_count = self.options.count
            self.options.count = None

        self.start_format(account=account)
        for transaction in self.do(command, account, backends=account.backend):
            if end_date is not None and transaction.date < end_date:
                break
            self.format(transaction)

        if end_date is not None:
            self.options.count = old_count

    def complete_history(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    @defaultcount(10)
    def do_history(self, line):
        """
        history ID [END_DATE]

        Display history of transactions.

        If END_DATE is supplied, list all transactions until this date.
        """
        return self.show_history('iter_history', line)

    def complete_coming(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    @defaultcount(10)
    def do_coming(self, line):
        """
        coming ID [END_DATE]

        Display future transactions.

        If END_DATE is supplied, show all transactions until this date.
        """
        return self.show_history('iter_coming', line)

    def complete_transfer(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()
        if len(args) == 3:
            return self._complete_account(args[1])

    def do_transfer(self, line):
        """
        transfer ACCOUNT [RECIPIENT AMOUNT [REASON]]

        Make a transfer beetwen two account
        - ACCOUNT    the source account
        - RECIPIENT  the recipient
        - AMOUNT     amount to transfer
        - REASON     reason of transfer

        If you give only the ACCOUNT parameter, it lists all the
        available recipients for this account.
        """
        id_from, id_to, amount, reason = self.parse_command_args(line, 4, 1)

        account = self.get_object(id_from, 'get_account', [])
        if not account:
            print('Error: account %s not found' % id_from, file=self.stderr)
            return 1

        if not id_to:
            self.objects = []
            self.set_formatter('recipient_list')
            self.set_formatter_header(u'Available recipients')

            self.start_format()
            for recipient in self.do('iter_transfer_recipients', account.id, backends=account.backend):
                self.cached_format(recipient)
            return 0

        id_to, backend_name_to = self.parse_id(id_to)

        if account.backend != backend_name_to:
            print("Transfer between different backends is not implemented", file=self.stderr)
            return 4

        try:
            amount = Decimal(amount)
        except (TypeError, ValueError, InvalidOperation):
            print('Error: please give a decimal amount to transfer', file=self.stderr)
            return 2

        if self.interactive:
            # Try to find the recipient label. It can be missing from
            # recipients list, for example for banks which allow transfers to
            # arbitrary recipients.
            to = id_to
            for recipient in self.do('iter_transfer_recipients', account.id, backends=account.backend):
                if recipient.id == id_to:
                    to = recipient.label
                    break

            print('Amount: %s%s' % (amount, account.currency_text))
            print('From:   %s' % account.label)
            print('To:     %s' % to)
            print('Reason: %s' % (reason or ''))
            if not self.ask('Are you sure to do this transfer?', default=True):
                return

        self.start_format()
        for transfer in self.do('transfer', account.id, id_to, amount, reason, backends=account.backend):
            self.format(transfer)

    def do_investment(self, id):
        """
        investment ID

        Display investments of an account.
        """
        account = self.get_object(id, 'get_account', [])
        if not account:
            print('Error: account "%s" not found (Hint: try the command "list")' % id, file=self.stderr)
            return 2

        self.start_format()
        for investment in self.do('iter_investment', account, backends=account.backend):
            self.format(investment)

    def do_budgea(self, line):
        """
        budgea USERNAME PASSWORD

        Export your bank accounts and transactions to Budgea.

        Budgea is an online web and mobile application to manage your bank
        accounts. To avoid giving your credentials to this service, you can use
        this command.

        https://www.budgea.com
        """
        username, password = self.parse_command_args(line, 2, 2)

        client = APIBrowser(baseurl='https://budgea.biapi.pro/2.0/')
        client.set_profile(Weboob(self.VERSION))
        try:
            r = client.request('auth/token', data={'username': username, 'password': password, 'application': 'weboob'})
        except BrowserHTTPError as r:
            error = r.response.json()
            print('Error: %s' % (error['message'] or error['code']), file=self.stderr)
            return 1

        client.session.headers['Authorization'] = 'Bearer %s' % r['token']

        accounts = {}
        for account in client.request('users/me/accounts')['accounts']:
            if account['id_connection'] is None:
                accounts[account['number']] = account

        for account in self.do('iter_accounts'):
            if account.id not in accounts:
                r = client.request('users/me/accounts', data={'name':    account.label,
                                                              'balance': account.balance,
                                                              'number':  account.id,
                                                              })
                self.logger.debug(r)
                account_id = r['id']
            else:
                account_id = accounts[account.id]['id']

            transactions = []
            for tr in self.do('iter_history', account, backends=account.backend):
                transactions.append({'original_wording': tr.raw,
                                     'simplified_wording': tr.label,
                                     'value': tr.amount,
                                     'date': tr.date.strftime('%Y-%m-%d'),
                                     })
            r = client.request('users/me/accounts/%s/transactions' % account_id,
                               data={'transactions': transactions})
            client.request('users/me/accounts/%s' % account_id, data={'balance': account.balance})
            print('- %s (%s%s): %s new transactions' % (account.label, account.balance, account.currency_text, len(r)))

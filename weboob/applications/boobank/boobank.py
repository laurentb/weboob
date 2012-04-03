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


from decimal import Decimal
import sys

from weboob.capabilities.bank import ICapBank, Account, Transaction
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Boobank']


class QifFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'raw', 'amount', 'category')

    def start_format(self, **kwargs):
        self.output(u'!type:Bank')

    def format_obj(self, obj, alias):
        result = u'D%s\n' % obj.date.strftime('%d/%m/%y')
        result += u'T%s\n' % obj.amount
        if obj.category:
            result += u'N%s\n' % obj.category
        result += u'M%s\n' % obj.raw
        result += u'^\n'
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
            except (IndexError,AttributeError):
                _type = ''

        label = obj.label
        if not label and hasattr(obj, 'raw'):
            label = obj.raw
        return ' %-10s   %-12s %-50s %10.2f' % (obj.date.strftime('%Y-%m-%d'), _type[:12], label[:50], obj.amount)


class TransferFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'origin', 'recipient', 'amount')

    def format_obj(self, obj, alias):
        result = u'------- Transfer %s -------\n' % obj.fillud
        result += u'Date:       %s\n' % obj.date
        result += u'Origin:     %s\n' % obj.origin
        result += u'Recipient:  %s\n' % obj.recipient
        result += u'Amount:     %.2f\n' % obj.amount
        return result


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
            id = '#%s (%s)' % (alias, obj.backend)
        else:
            id = obj.fullid

        result = (u' %s%-' + (u'15' if alias is not None else '30') + u's%s %-25s  %8s   %8s') % \
                             (self.BOLD, id, self.NC,
                              obj.label, '%.2f' % obj.balance, '%.2f' % (obj.coming or Decimal(0.0)))

        self.tot_balance += obj.balance
        if obj.coming:
            self.tot_coming += obj.coming
        return result

    def flush(self):
        self.output(u'------------------------------------------%s+----------+----------' % (('-' * 15) if not self.interactive else ''))
        self.output(u'%s                                    Total   %8s   %8s' % ((' ' * 15) if not self.interactive else '',
                                                                               '%.2f' % self.tot_balance, '%.2f' % self.tot_coming))
        self.tot_balance = Decimal(0)
        self.tot_coming = Decimal(0)


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.c'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon, Christophe Benz'
    CAPS = ICapBank
    DESCRIPTION = "Console application allowing to list your bank accounts and get their balance, " \
                  "display accounts history and coming bank operations, and transfer money from an account to " \
                  "another (if available)."
    EXTRA_FORMATTERS = {'account_list':   AccountListFormatter,
                        'recipient_list': RecipientListFormatter,
                        'transfer':       TransferFormatter,
                        'qif':            QifFormatter,
                        'ops_list':       TransactionsFormatter,
                       }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'ls':          'account_list',
                           'list':        'account_list',
                           'transfer':    'transfer',
                           'history':     'ops_list',
                           'coming':      'ops_list',
                          }
    COLLECTION_OBJECTS = (Account, Transaction, )

    def _complete_account(self, exclude=None):
        if exclude:
            exclude = '%s@%s' % self.parse_id(exclude)

        return [s for s in self._complete_object() if s != exclude]

    def do_list(self, line):
        """
        list

        List accounts.
        """
        return self.do_ls(line)

    def complete_history(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    def do_history(self, id):
        """
        history ID

        Display old operations.
        """
        id, backend_name = self.parse_id(id)
        if not id:
            print >>sys.stderr, 'Error: please give an account ID (hint: use list command)'
            return 2
        names = (backend_name,) if backend_name is not None else None

        def do(backend):
            account = backend.get_account(id)
            return backend.iter_history(account)

        self.start_format()
        for backend, operation in self.do(do, backends=names):
            self.format(operation)
        self.flush()

    def complete_coming(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    def do_coming(self, id):
        """
        coming ID

        Display all future operations.
        """
        id, backend_name = self.parse_id(id)
        names = (backend_name,) if backend_name is not None else None

        def do(backend):
            account = backend.get_account(id)
            return backend.iter_coming(account)

        self.start_format(id=id)
        for backend, operation in self.do(do, backends=names):
            self.format(operation)
        self.flush()

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

        id_from, backend_name_from = self.parse_id(id_from)
        if not id_to:
            self.objects = []
            self.set_formatter('recipient_list')
            self.set_formatter_header(u'Available recipients')
            names = (backend_name_from,) if backend_name_from is not None else None

            self.start_format()
            for backend, recipient in self.do('iter_transfer_recipients', id_from, backends=names):
                self.cached_format(recipient)
            self.flush()
            return 0

        id_to, backend_name_to = self.parse_id(id_to)

        try:
            amount = Decimal(amount)
        except (TypeError, ValueError):
            print >>sys.stderr, 'Error: please give a decimal amount to transfer'
            return 2

        if backend_name_from != backend_name_to:
            print >>sys.stderr, "Transfer between different backends is not implemented"
            return 4
        else:
            backend_name = backend_name_from

        names = (backend_name,) if backend_name is not None else None

        self.start_format()
        for backend, transfer in self.do('transfer', id_from, id_to, amount, reason, backends=names):
            self.format(transfer)
        self.flush()

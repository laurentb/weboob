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


import sys

from weboob.capabilities.bank import ICapBank
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Boobank']


class TransferFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'date', 'origin', 'recipient', 'amount')

    def flush(self):
        pass

    def format_dict(self, item):
        result = u'------- Transfer %s -------\n' % item['id']
        result += u'Date:       %s\n' % item['date']
        result += u'Origin:     %s\n' % item['origin']
        result += u'Recipient:  %s\n' % item['recipient']
        result += u'Amount:     %.2f\n' % item['amount']
        return result

class RecipientListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'label')

    count = 0

    def flush(self):
        self.count = 0

    def format_dict(self, item):
        self.count += 1

        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            id = '#%d (%s)' % (self.count, backend)
        else:
            id = item['id']

        return u'%s %-30s  %s %s' % (self.BOLD, id, self.NC, item['label'])

class AccountListFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'label', 'balance', 'coming')

    count = 0
    tot_balance = 0.0
    tot_coming = 0.0


    def flush(self):
        result = u'------------------------------------------%s+----------+----------\n' % (('-' * 15) if not self.interactive else '')
        result +=u'%s                                    Total   %8s   %8s' % ((' ' * 15) if not self.interactive else '',
                                                                               '%.2f' % self.tot_balance, '%.2f' % self.tot_coming)
        self.after_format(result)
        self.tot_balance = 0.0
        self.tot_coming = 0.0
        self.count = 0

    def format_dict(self, item):
        self.count += 1
        if self.interactive:
            backend = item['id'].split('@', 1)[1]
            id = '#%d (%s)' % (self.count, backend)
        else:
            id = item['id']

        result = u''
        if self.count == 1:
            result += '               %s  Account                     Balance    Coming \n' % ((' ' * 15) if not self.interactive else '')
            result += '------------------------------------------%s+----------+----------\n' % (('-' * 15) if not self.interactive else '')
        result += (u' %s%-' + (u'15' if self.interactive else '30') + u's%s %-25s  %8s   %8s') % \
                             (self.BOLD, id, self.NC,
                              item['label'], '%.2f' % item['balance'], '%.2f' % (item['coming'] or 0.0))

        self.tot_balance += item['balance']
        if item['coming']:
            self.tot_coming += item['coming']
        return result


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.8'
    COPYRIGHT = 'Copyright(C) 2010-2011 Romain Bignon, Christophe Benz'
    CAPS = ICapBank
    DESCRIPTION = "Console application allowing to list your bank accounts and get their balance, " \
                  "display accounts history and coming bank operations, and transfer money from an account to " \
                  "another (if available)."
    EXTRA_FORMATTERS = {'account_list':   AccountListFormatter,
                        'recipient_list': RecipientListFormatter,
                        'transfer':       TransferFormatter,
                       }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'ls':          'account_list',
                           'transfer':    'transfer',
                          }

    def _complete_account(self, exclude=None):
        if exclude:
            exclude = '%s@%s' % self.parse_id(exclude)

        return [s for s in self._complete_object() if s != exclude]

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
            return backend.iter_operations(account)

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
            for backend, recipient in self.do('iter_transfer_recipients', id_from, backends=[backend_name_from]):
                self.format(recipient)
                self.add_object(recipient)
            self.flush()
            return 0

        id_to, backend_name_to = self.parse_id(id_to)

        try:
            amount = float(amount)
        except (TypeError,ValueError):
            print >>sys.stderr, 'Error: please give a decimal amount to transfer'
            return 2

        if backend_name_from != backend_name_to:
            print >>sys.stderr, "Transfer between different backends is not implemented"
            return 4
        else:
            backend_name = backend_name_from

        names = (backend_name,) if backend_name is not None else None

        for backend, transfer in self.do('transfer', id_from, id_to, amount, reason, backends=names):
            self.format(transfer)
        self.flush()

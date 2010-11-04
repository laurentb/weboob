# -*- coding: utf-8 -*-

# Copyright(C) 2009-2010  Romain Bignon, Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import sys

from weboob.capabilities.bank import ICapBank
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter


__all__ = ['Boobank']


class TransferFormatter(IFormatter):
    def flush(self):
        pass

    def format_dict(self, item):
        result = u'------- Transfer %s -------\n' % item['id']
        result += u'Date:       %s\n' % item['date']
        result += u'Origin:     %s\n' % item['origin']
        result += u'Recipient:  %s\n' % item['recipient']
        result += u'Amount:     %.2f\n' % item['amount']
        return result

class AccountListFormatter(IFormatter):
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
                             (ReplApplication.BOLD, id, ReplApplication.NC,
                              item['label'], '%.2f' % item['balance'], '%.2f' % (item['coming'] or 0.0))

        self.tot_balance += item['balance']
        if item['coming']:
            self.tot_coming += item['coming']
        return result


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.3.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon, Christophe Benz'
    CAPS = ICapBank
    EXTRA_FORMATTERS = {'account_list': AccountListFormatter,
                        'transfer':     TransferFormatter,
                       }
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'list':        'account_list',
                           'transfer':    'transfer',
                          }

    accounts = []

    def do_list(self, line):
        """
        list

        List every available accounts.
        """
        tot_balance = 0.0
        tot_coming = 0.0
        self.accounts = []
        for backend, account in self.do('iter_accounts'):
            self.format(account)
            tot_balance += account.balance
            if account.coming:
                tot_coming += account.coming
            self.accounts.append(account)
        self.flush()

    def _complete_account(self, exclude=None):
        if exclude:
            id, backend = self.parse_id(exclude)
        return ['%s@%s' % (acc.id, acc.backend) for acc in self.accounts if not exclude or (acc.id != id and acc.backend == backend)]

    def complete_history(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_account()

    def parse_id(self, id):
        if self.interactive:
            try:
                account = self.accounts[int(id) - 1]
            except (IndexError,ValueError):
                pass
            else:
                return account.id, account.backend
        return ReplApplication.parse_id(self, id)

    def do_history(self, id):
        """
        history ID

        Display old operations.
        """
        id, backend_name = self.parse_id(id)
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
        transfer ACCOUNT [TO AMOUNT [REASON]]

        Make a transfer beetwen two account
        - ACCOUNT the source account
        - TO      the recipient
        - AMOUNT  amount to transfer
        - REASON  reason of transfer

        If you give only the ACCOUNT parameter, it lists all the
        available recipients for this account.
        """
        id_from, id_to, amount, reason = self.parseargs(line, 4, 1)

        id_from, backend_name_from = self.parse_id(id_from)
        if not id_to:
            print >>sys.stderr, 'Error: listing recipient is not implemented yet'
            return

        id_to, backend_name_to = self.parse_id(id_to)

        try:
            amount = float(amount)
        except (TypeError,ValueError):
            print >>sys.stderr, 'Error: please give a decimal amount to transfer'
            return 1

        if backend_name_from != backend_name_to:
            print >>sys.stderr, "Transfer between different backends is not implemented"
            return
        else:
            backend_name = backend_name_from

        names = (backend_name,) if backend_name is not None else None

        for backend, transfer in self.do('transfer', id_from, id_to, amount, reason, backends=names):
            self.format(transfer)
        self.flush()

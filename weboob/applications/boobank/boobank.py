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

from __future__ import with_statement

from weboob.capabilities.bank import ICapBank
from weboob.tools.application.repl import ReplApplication


__all__ = ['Boobank']


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.3'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon, Christophe Benz'
    CAPS = ICapBank
    DEFAULT_FORMATTER = 'table'
    COMMANDS_FORMATTERS = {'transfer':    'multiline'}

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
        else:
            self.format((('id',     ''),
                         ('label', 'Total'),
                         ('balance', tot_balance),
                         ('coming', tot_coming)))
        self.flush()

    def _complete_account(self, exclude=None):
        if exclude:
            id, backend = self.parse_id(exclude)
        return ['%s@%s' % (acc.id, acc.backend) for acc in self.accounts if not exclude or (acc.id != id and acc.backend == backend)]

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
        transfer FROM TO AMOUNT

        Make a transfer beetwen two account
        """
        id_from, id_to, amount = self.parseargs(line, 3, 3)

        id_from, backend_name_from = self.parse_id(id_from)
        id_to, backend_name_to = self.parse_id(id_to)

        if backend_name_from != backend_name_to:
            print "Transfer between different backend is not implemented"
            return
        else:
            backend_name = backend_name_from

        names = (backend_name,) if backend_name is not None else None

        def do(backend):
            return backend.transfer(id_from, id_to, float(amount))

        for backend, id_transfer in self.do(do, backends=names):
            self.format((('Transfer', str(id_transfer)),))
        self.flush()

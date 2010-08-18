#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ft=python et softtabstop=4 cinoptions=4 shiftwidth=4 ts=4 ai

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

import logging

import weboob
from weboob.capabilities.bank import ICapBank
from weboob.tools.application.repl import ReplApplication


__all__ = ['Boobank']


class Boobank(ReplApplication):
    APPNAME = 'boobank'
    VERSION = '0.1'
    COPYRIGHT = 'Copyright(C) 2010 Romain Bignon, Christophe Benz'

    def load_default_backends(self):
        self.load_backends(ICapBank)

    def do_list(self, line):
        """
        List every available accounts.
        """
        tot_balance = 0.0
        tot_coming = 0.0
        try:
            for backend, account in self.do('iter_accounts'):
                self.format(account)
                tot_balance += account.balance
                tot_coming += account.coming
        except weboob.core.CallErrors, errors:
            for backend, error, backtrace in errors:
                if isinstance(error, weboob.tools.browser.BrowserIncorrectPassword):
                    logging.error(u'Error: Incorrect password for backend %s' % backend.name)
                else:
                    logging.error(u'Error[%s]: %s\n%s' % (backend.name, error, backtrace))
        else:
            self.format((('label', 'Total'),
                         ('balance', tot_balance),
                         ('coming', tot_coming)))

    def do_history(self, id):
        """
        Display old operations.
        """
        id, backend_name = self.parse_id(id)
        names = (backend_name,) if backend_name is not None else None
        self.load_backends(ICapBank, names=names)

        def do(backend):
            account = backend.get_account(id)
            return backend.iter_history(account)

        for backend, operation in self.do(do):
            self.format(operation)

    def do_coming(self, id):
        """
        Display all future operations.
        """
        id, backend_name = self.parse_id(id)
        names = (backend_name,) if backend_name is not None else None
        self.load_backends(ICapBank, names=names)

        def do(backend):
            account = backend.get_account(id)
            return backend.iter_operations(account)

        for backend, operation in self.do(do):
            self.format(operation)

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ft=python et softtabstop=4 cinoptions=4 shiftwidth=4 ts=4 ai

"""
Copyright(C) 2009-2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from __future__ import with_statement

import sys

import weboob
from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.application import ConsoleApplication


__all__ = ['Boobank']


class Boobank(ConsoleApplication):
    APPNAME = 'boobank'

    def main(self, argv):
        self.load_backends(ICapBank, names=self.enabled_backends)
        return self.process_command(*argv[1:])

    @ConsoleApplication.command('List every available accounts')
    def command_list(self):
        results = {'HEADER': ('ID', 'label', 'balance', 'coming')}
        for backend in self.weboob.iter_backends():
            rows = []
            try:
                for account in backend.iter_accounts():
                    row = [account.id, account.label, account.balance, account.coming]
                    rows.append(row)
            except weboob.tools.browser.BrowserIncorrectPassword:
                print >>sys.stderr, 'Error: Incorrect password for backend %s' % backend.name
                return 1
        results[backend.name] = rows
        return results

    @ConsoleApplication.command('Display all future operations')
    def command_coming(self, id):
        operations = []
        found = 0
        for backend in self.weboob.iter_backends():
            try:
                account = backend.get_account(id)
            except AccountNotFound:
                if found == 0:
                    found = -1
            else:
                found = 1
                for operation in backend.iter_operations(account):
                    operations.append('  %8s   %-50s   %11.2f' % (operation.date, operation.label, operation.amount))
        if found < 0:
            print >>sys.stderr, "Error: account %s not found" % id
            return 1
        else:
            if operations:
                print '      Date   Label                                                     Amount  '
                print '+----------+----------------------------------------------------+-------------+'
                print '\n'.join(operations)
            else:
                print 'No coming operations for ID=%s' % id

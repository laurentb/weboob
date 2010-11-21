# -*- coding: utf-8 -*-

# Copyright(C) 2010  Jocelyn Jaubert
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


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.bank import ICapBank, AccountNotFound, Account
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import SocieteGenerale


__all__ = ['SocieteGeneraleBackend']


class SocieteGeneraleBackend(BaseBackend, ICapBank):
    NAME = 'societegenerale'
    MAINTAINER = 'Jocelyn Jaubert'
    EMAIL = 'jocelyn.jaubert@gmail.com'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'Société Générale french bank\' website'
    CONFIG = ValuesDict(Value('login',      label='Account ID'),
                        Value('password',   label='Password', masked=True))
    BROWSER = SocieteGenerale

    def create_default_browser(self):
        return self.create_browser(self.config['login'],
                                   self.config['password'])

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        print _id
        if not _id.isdigit():
            raise AccountNotFound()
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

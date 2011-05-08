# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


# python2.5 compatibility
from __future__ import with_statement

from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import SocieteGenerale


__all__ = ['SocieteGeneraleBackend']


class SocieteGeneraleBackend(BaseBackend, ICapBank):
    NAME = 'societegenerale'
    MAINTAINER = 'Jocelyn Jaubert'
    EMAIL = 'jocelyn.jaubert@gmail.com'
    VERSION = '0.9'
    LICENSE = 'AGPLv3+'
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

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Gilles-Alexandre Quenot
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
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import Fortuneo


__all__ = ['FortuneoBackend']


class FortuneoBackend(BaseBackend, ICapBank):
    NAME = 'fortuneo'
    MAINTAINER = 'Gilles-Alexandre Quenot'
    EMAIL = 'gilles.quenot@gmail.com'
    VERSION = '0.c'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Fortuneo French bank website'
    CONFIG = BackendConfig(ValueBackendPassword('login',      label='Account ID', masked=False, required=True),
                           ValueBackendPassword('password',   label='Password', required=True))
    BROWSER = Fortuneo

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
	# _id = "fortuneo"
	#print "DEBUG\n\n\n", _id, "DEBUG\n\n\n"
        if not _id.isdigit():
            raise AccountNotFound()
        with self.browser:
            account = self.browser.get_account(_id)
	    print "DEBUG 2\n\n\n", account, "\n\n\nEND DEBUG 2"
        if account:
            return account
        else:
	    raise AccountNotFound()

    def iter_history(self, account):
        pass
        #with self.browser:
        #    for tr in self.browser.iter_history(account._link_id):
        #        if not tr._coming:
        #            yield tr

    def iter_coming(self, account):
        with self.browser:
            for tr in self.browser.iter_history(account._link_id):
                if tr._coming:
                    yield tr

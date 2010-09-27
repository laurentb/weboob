# -*- coding: utf-8 -*-
#
#       backend.py
#
#       Copyright 2010 nicolas <nicolas@jombi.fr>
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

from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend

from .browser import BPbrowser

class BPBackend(BaseBackend, ICapBank):
    NAME = 'bp'
    MAINTAINER = 'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.2'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'La banque postale, French bank'
    CONFIG = {'login':    BaseBackend.ConfigField(description='Account ID'),
              'password': BaseBackend.ConfigField(description='Password of account', is_masked=True)
             }
    BROWSER = BPbrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'], self.config['password'])

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        for history in self.browser.get_history(account):
            yield history

    def transfer(self, id_from, id_to, amount):
        from_account = self.get_account(id_from)
        to_account = self.get_account(id_to)

        #TODO: retourner le numero du virement
        self.browser.make_transfer(from_account, to_account, amount)

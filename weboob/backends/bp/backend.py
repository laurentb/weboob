# -*- coding: utf-8 -*-

# Copyright(C) 2010  Nicolas Duhamel
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
from weboob.tools.value import ValuesDict, Value

from .browser import BPBrowser


__all__ = ['BPBackend']


class BPBackend(BaseBackend, ICapBank):
    NAME = 'bp'
    MAINTAINER = 'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.7.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u'La banque postale, French bank'
    CONFIG = ValuesDict(Value('login',    label='Account ID'),
                        Value('password', label='Password', masked=True))
    BROWSER = BPBrowser

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
   
    def transfer(self, id_from, id_to, amount, reason=None):
        from_account = self.get_account(id_from)
        to_account = self.get_account(id_to)

        #TODO: retourner le numero du virement
        #TODO: support the 'reason' parameter
        return self.browser.make_transfer(from_account, to_account, amount)

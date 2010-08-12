# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

from .browser import Cragr


class CragrBackend(BaseBackend, ICapBank):
    NAME = 'cragr'
    MAINTAINER = 'Laurent Bachelier'
    EMAIL = 'laurent@bachelier.name'
    VERSION = '0.1'
    DESCRIPTION = 'Credit Agricole french bank\'s website'
    LICENSE = 'GPLv3'
    CONFIG = {'login':    BaseBackend.ConfigField(description='Account ID'),
              'password': BaseBackend.ConfigField(description='Password of account', is_masked=True),
              'website':  BaseBackend.ConfigField(description='What website to use', default='m.lefil.com'),
             }
    BROWSER = Cragr

    def create_default_browser(self):
        return self.create_browser(self.config['website'], self.config['login'], self.config['password'])

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        try:
            _id = long(_id)
        except ValueError:
            raise AccountNotFound()
        else:
            account = self.browser.get_account(_id)
            if account:
                return account
            else:
                raise AccountNotFound()

    def iter_operations(self, account):
        """ Not supported yet """
        return iter([])

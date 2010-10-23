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

from .browser import BNPorc


__all__ = ['BNPorcBackend']


class BNPorcBackend(BaseBackend, ICapBank):
    NAME = 'bnporc'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.3'
    LICENSE = 'GPLv3'
    DESCRIPTION = 'BNP Paribas french bank\' website'
    CONFIG = {'login':    BaseBackend.ConfigField(description='Account ID'),
              'password': BaseBackend.ConfigField(description='Password of account', is_masked=True),
              'rotating_password': BaseBackend.ConfigField(
                           description='Password to set when the allowed uses are exhausted (6 digits)',
                           default='',
                           regexp='^(\d{6}|)$'),
             }
    BROWSER = BNPorc

    def create_default_browser(self):
        if self.config['rotating_password'].isdigit() and len(self.config['rotating_password']) == 6:
            rotating_password = self.config['rotating_password']
        else:
            rotating_password = None
        return self.create_browser(self.config['login'],
                                   self.config['password'],
                                   password_changed_cb=self._password_changed_cb,
                                   rotating_password=rotating_password)

    def _password_changed_cb(self, old, new):
        new_settings = {'password':          new,
                        'rotating_password': old,
                       }
        self.weboob.backends_config.edit_backend(self.name, self.NAME, new_settings)

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

    def iter_history(self, account):
        for history in self.browser.get_history(account):
            yield history

    def iter_operations(self, account):
        for coming in self.browser.get_coming_operations(account):
            yield coming

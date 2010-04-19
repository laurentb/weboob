# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Christophe Benz

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

from weboob.capabilities.bank import ICapBank
from weboob.tools.application import BaseApplication, ConfigError

class MonFric(BaseApplication):
    APPNAME = 'monfric'
    CONFIG = dict(backend='', account='')

    def main(self, argv):
        self.load_config()
        requested_backend = self.config.get('backend')
        requested_account = self.config.get('account')
        if not requested_backend or not requested_account :
            raise ConfigError(u'Please provide "backend" and "account" keys in config file "%s".' % self.config.path)
        self.weboob.load_backends(ICapBank)
        for account in self.weboob.backends[requested_backend].iter_accounts():
            if account.label == requested_account:
                print account.balance

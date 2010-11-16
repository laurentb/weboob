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
from weboob.tools.value import ValuesDict, Value

from .browser import Cragr


__all__ = ['CragrBackend']


class CragrBackend(BaseBackend, ICapBank):
    NAME = 'cragr'
    MAINTAINER = 'Xavier Guerrin'
    EMAIL = 'xavier@tuxfamily.org'
    VERSION = '0.4'
    DESCRIPTION = 'Credit Agricole french bank\'s website'
    LICENSE = 'GPLv3'
    website_choices = dict((k, u'%s (%s)' % (v, k)) for k, v in {
        'm.lefil.com': u'Pyrénées Gascogne',
        'm.ca-pca.fr': u'Provence Alpes Côte d\'Azur',
        }.iteritems())
    CONFIG = ValuesDict(Value('website',  label='Website to use', choices=website_choices),
                        Value('login',    label='Account ID'),
                        Value('password', label='Password', masked=True))
    BROWSER = Cragr

    def create_default_browser(self):
        return self.create_browser(self.config['website'], self.config['login'], self.config['password'])

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        if not _id.isdigit():
            raise AccountNotFound()
        account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        for history in self.browser.get_history(account):
            yield history

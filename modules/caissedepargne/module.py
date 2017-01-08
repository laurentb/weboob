# -*- coding: utf-8 -*-

# Copyright(C) 2012-2013 Romain Bignon
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


from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.contact import CapContact
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.ordereddict import OrderedDict

from .browser import CaisseEpargne


__all__ = ['CaisseEpargneModule']


class CaisseEpargneModule(Module, CapBank, CapContact):
    NAME = 'caissedepargne'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.3'
    DESCRIPTION = u'Caisse d\'Épargne'
    LICENSE = 'AGPLv3+'
    BROWSER = CaisseEpargne
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.caisse-epargne.fr':     u'Caisse d\'Épargne',
        'www.banquebcp.fr':          u'Banque BCP',
        }.iteritems(), key=lambda k_v: (k_v[1], k_v[0]))])
    CONFIG = BackendConfig(Value('website',  label='Banque', choices=website_choices, default='www.caisse-epargne.fr'),
                           ValueBackendPassword('login',    label='Identifiant client', masked=False),
                           ValueBackendPassword('password', label='Code personnel', regexp='\d+'),
                           Value('nuser',                   label='User ID (optional)', default=''))

    def create_default_browser(self):
        return self.create_browser(nuser=self.config['nuser'].get(),
                                   username=self.config['login'].get(),
                                   password=self.config['password'].get(),
                                   domain=self.config['website'].get())


    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account
        for account in self.browser.get_loans_list():
            yield account

    def get_account(self, _id):
        account = self.browser.get_account(_id)

        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        return self.browser.get_history(account)

    def iter_coming(self, account):
        return self.browser.get_coming(account)

    def iter_investment(self, account):
        return self.browser.get_investment(account)

    def iter_contacts(self):
        return self.browser.get_advisor()

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

from collections import OrderedDict

from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import CreditDuNordBrowser


__all__ = ['CreditDuNordModule']


class CreditDuNordModule(Module, CapBank, CapProfile):
    NAME = 'creditdunord'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'Crédit du Nord, Banque Courtois, Kolb, Nuger, Laydernier, Tarneaud, Société Marseillaise de Crédit'
    LICENSE = 'AGPLv3+'
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'www.credit-du-nord.fr':     u'Crédit du Nord',
        'www.banque-courtois.fr':    u'Banque Courtois',
        'www.banque-kolb.fr':        u'Banque Kolb',
        'www.banque-laydernier.fr':  u'Banque Laydernier',
        'www.banque-nuger.fr':       u'Banque Nuger',
        'www.banque-rhone-alpes.fr': u'Banque Rhône-Alpes',
        'www.tarneaud.fr':           u'Tarneaud',
        'www.smc.fr':                u'Société Marseillaise de Crédit',
        }.items(), key=lambda k_v: (k_v[1], k_v[0]))])
    CONFIG = BackendConfig(Value('website',  label='Banque', choices=website_choices, default='www.credit-du-nord.fr'),
                           ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code confidentiel'))
    BROWSER = CreditDuNordBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

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
        account = self.get_account(account.id)
        for tr in self.browser.get_history(account):
            if not tr._is_coming:
                yield tr

    def iter_coming(self, account):
        account = self.get_account(account.id)
        for tr in self.browser.get_history(account, coming=True):
            if tr._is_coming:
                yield tr

    def iter_investment(self, account):
        account = self.get_account(account.id)
        return self.browser.get_investment(account)

    def get_profile(self):
        return self.browser.get_profile()

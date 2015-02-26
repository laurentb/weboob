# -*- coding: utf-8 -*-

# Copyright(C) 2015 Christophe Lampin

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

from weboob.capabilities.base import find_object
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.ordereddict import OrderedDict

from .browser import Esalia, Capeasi, EREHSBC, BNPPERE


__all__ = ['S2eModule']


class S2eModule(Module, CapBank):
    NAME = 's2e'
    MAINTAINER = u'Christophe Lampin'
    EMAIL = 'weboob@lampin.net'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'S2e module for Employee Savings Plans. Support for Esalia, Capeasi, "BNP Paribas Épargne & Retraite Entreprises" and "HSBC Epargne et Retraite en Entreprise"'

    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'm.esalia.com':             u'Esalia',                  # Good Url. Tested
        'mobile.capeasi.com':       u'Capeasi',                 # Good Url. Not fully tested
        'mobi.ere.hsbc.fr':         u'ERE HSBC',                # Good Url. Not fully tested
        'smartphone.s2e-net.com':   u'BNPP ERE',                # Url To Confirm. Not tested
        # 'smartphone.s2e-net.com':   u'Groupe Crédit du Nord',  # Mobile version not available yet.
    }.iteritems(), key=lambda k_v: (k_v[1], k_v[0]))])

    BROWSERS = {
        'm.esalia.com':             Esalia,
        'mobile.capeasi.com':       Capeasi,
        'mobi.ere.hsbc.fr':         EREHSBC,
        'smartphone.s2e-net.com':   BNPPERE,
        # 'smartphone.s2e-net.com':  CreditNord,  # Mobile version not available yet.
    }

    CONFIG = BackendConfig(Value('website',  label='Banque', choices=website_choices, default='smartphone.s2e-net.com'),
                           ValueBackendPassword('login',      label='Identifiant', masked=False),
                           ValueBackendPassword('password',   label='Code secret', regexp='^(\d{6}|)$'))

    def create_default_browser(self):
        self.BROWSER = self.BROWSERS[self.config['website'].get()]
        return self.create_browser(self.config['website'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        return self.browser.get_accounts_list()

    def get_account(self, _id):
        return find_object(self.browser.get_accounts_list(), id=_id, error=AccountNotFound)

    def iter_history(self, account):
        return self.browser.iter_history(account)
# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object

from .browser import EsaliaBrowser, CapeasiBrowser, ErehsbcBrowser, BnppereBrowser


__all__ = ['S2eModule']


class S2eModule(Module, CapBank):
    NAME = 's2e'
    DESCRIPTION = u'Épargne Salariale'
    MAINTAINER = u'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    CONFIG = BackendConfig(
             ValueBackendPassword('login',    label='Identifiant', masked=False),
             ValueBackendPassword('password', label='Code secret', regexp='^(\d{6})$'),
             ValueBackendPassword('secret',   label=u'Réponse secrète (optionnel)', default=''),
             Value('otp',     label=u'Code de sécurité', default='', regexp='^(\d{6})$'),
             Value('website', label='Banque', default='', choices={'esalia': u'Esalia',
                                                                   'capeasi': u'Capeasi',
                                                                   'erehsbc': u'ERE HSBC',
                                                                   'bnppere': u'BNPP ERE'}))

    BROWSERS = {
        'esalia':  EsaliaBrowser,
        'capeasi': CapeasiBrowser,
        'erehsbc': ErehsbcBrowser,
        'bnppere': BnppereBrowser,
    }

    def create_default_browser(self):
        self.BROWSER = self.BROWSERS[self.config['website'].get()]
        return self.create_borser(self.config)

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_pocket(self, account):
        return self.browser.iter_pocket(account)

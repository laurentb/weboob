# -*- coding: utf-8 -*-

# Copyright(C) 2015      Baptiste Delpey
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.base import find_object
from weboob.tools.value import ValueBackendPassword, Value

from .proxy_browser import ProxyBrowser


__all__ = ['BnpcartesentrepriseModule']


class BnpcartesentrepriseModule(Module, CapBank):
    NAME = 'bnpcards'
    DESCRIPTION = u'BNP Cartes Entreprises'
    MAINTAINER = u'Baptiste Delpey'
    EMAIL = 'bdelpey@budget-insight.fr'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Code personnel'),
                           Value('type', label='Profil de connexion', default='1',
                                 choices={'1': 'Titulaire',
                                          '2': 'Gestionnaire'}))

    BROWSER = ProxyBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['type'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        for acc in self.browser.iter_accounts():
            acc._bisoftcap = {'all': {'softcap_day':5,'day_for_softcap':100}}
            yield acc

    def iter_coming(self, account):
        for tr in self.browser.get_transactions(account):
            if tr._coming:
                yield tr

    def iter_history(self, account):
        for tr in self.browser.get_transactions(account):
            if not tr._coming:
                yield tr

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Kevin Pouget
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

from weboob.capabilities.bank import CapBankTransferAddRecipient
from weboob.capabilities.profile import CapProfile
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import CreditCooperatif


__all__ = ['CreditCooperatifModule']


class CreditCooperatifModule(AbstractModule, CapBankTransferAddRecipient, CapProfile):
    NAME = 'creditcooperatif'
    MAINTAINER = u'Kevin Pouget'
    EMAIL = 'weboob@kevin.pouget.me'
    VERSION = '1.4'
    DESCRIPTION = u'Crédit Coopératif'
    LICENSE = 'AGPLv3+'
    auth_type = {'particular': "Interface Particuliers",
                 'weak' : "Code confidentiel (pro)",
                 'strong': "Sesame (pro)"}
    CONFIG = BackendConfig(Value('auth_type', label='Type de compte', choices=auth_type, default="particular"),
                           ValueBackendPassword('login', label='Code utilisateur', masked=False),
                           ValueBackendPassword('password', label='Code personnel', regexp='\d+'))

    PARENT = 'caissedepargne'
    BROWSER = CreditCooperatif

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get(), weboob=self.weboob)

# -*- coding: utf-8 -*-

# Copyright(C) 2013      Noe Rubinstein
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

from weboob.capabilities.bank import CapBank
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import DelubacBrowser


__all__ = ['DelubacModule']


class DelubacModule(AbstractModule, CapBank):
    NAME = 'delubac'
    DESCRIPTION = u'Banque Delubac & Cie'
    MAINTAINER = u'Noe Rubinstein'
    EMAIL = 'nru@budget-insight.com'
    VERSION = '2.0'
    LICENSE = 'LGPLv3+'

    BROWSER = DelubacBrowser

    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe', regexp='^\d+$'))
    PARENT = 'themisbanque'

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get(),
                                   weboob=self.weboob)


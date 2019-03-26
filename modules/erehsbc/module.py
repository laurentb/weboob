# -*- coding: utf-8 -*-

# Copyright(C) 2016      Edouard Lambert
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


from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value
from weboob.capabilities.bank import CapBank

from .browser import ErehsbcBrowser


__all__ = ['ErehsbcModule']


class ErehsbcModule(AbstractModule, CapBank):
    NAME = 'erehsbc'
    DESCRIPTION = u'HSBC Épargne Salariale'
    MAINTAINER = u'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'
    CONFIG = BackendConfig(
             ValueBackendPassword('login',    label='Identifiant', masked=False),
             ValueBackendPassword('password', label='Code secret', regexp='^(\d{6})$'),
             Value('otp', label=u'Code de sécurité', default='', regexp='^(\d{6})$'))

    BROWSER = ErehsbcBrowser
    PARENT = 's2e'

    def create_default_browser(self):
        return self.create_browser(self.config, weboob=self.weboob)

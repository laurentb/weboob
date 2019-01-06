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

from weboob.capabilities.bank import CapBank
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import GanAssurances


__all__ = ['GanAssurancesModule']


class GanAssurancesModule(AbstractModule, CapBank):
    NAME = 'ganassurances'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    DESCRIPTION = u'Gan Assurances'
    LICENSE = 'AGPLv3+'
    website_choices = OrderedDict([(k, u'%s (%s)' % (v, k)) for k, v in sorted({
        'espaceclient.groupama.fr':             u'Groupama Banque',
        'espaceclient.ganassurances.fr':        u'Gan Assurances',
        'espaceclient.ganpatrimoine.fr':        U'Gan Patrimoine',
        }.items(), key=lambda k_v: (k_v[1], k_v[0]))])
    CONFIG = BackendConfig(Value('website',  label='Banque', choices=website_choices, default='espaceclient.ganassurances.fr'),
                           ValueBackendPassword('login',    label=u'Numéro client', masked=False),
                           ValueBackendPassword('password', label=u"Code d'accès"))
    BROWSER = GanAssurances
    PARENT = 'groupama'

    def create_default_browser(self):
        return self.create_browser(self.config['website'].get(),
                                   self.config['login'].get(),
                                   self.config['password'].get(),
                                   weboob=self.weboob)

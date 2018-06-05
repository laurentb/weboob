# -*- coding: utf-8 -*-

# Copyright(C) 2013      Romain Bignon
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


from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword


__all__ = ['BanqueAccordModule']


class BanqueAccordModule(AbstractModule):
    NAME = 'banqueaccord'
    DESCRIPTION = u'Banque Accord'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', regexp='\d+', masked=False),
                           ValueBackendPassword('password', label=u"Code d'accès", regexp='\d+'))

    PARENT = 'oney'
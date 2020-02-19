# -*- coding: utf-8 -*-

# Copyright(C) 2017      Edouard Lambert
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

from __future__ import unicode_literals

from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBankWealth


__all__ = ['PradoepargneModule']


class PradoepargneModule(AbstractModule, CapBankWealth):
    NAME = 'pradoepargne'
    DESCRIPTION = 'Prado Épargne Salariale'
    MAINTAINER = 'Edouard Lambert'
    EMAIL = 'elambert@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'
    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', masked=False),
        ValueBackendPassword('password', label='Mot de passe')
    )

    PARENT = 'humanis'

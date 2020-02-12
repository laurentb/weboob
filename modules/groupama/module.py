# -*- coding: utf-8 -*-

# Copyright(C) 2012-2019  Budget Insight
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

from weboob.capabilities.bank import CapBank
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import GroupamaBrowser


__all__ = ['GroupamaModule']


class GroupamaModule(AbstractModule, CapBank):
    NAME = 'groupama'
    DESCRIPTION = 'Groupama'
    MAINTAINER = 'Quentin Defenouillere'
    EMAIL = 'quentin.defenouillere@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'

    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant / N° Client / Email / Mobile', masked=False),
        ValueBackendPassword('password', label='Mon mot de passe', regexp=r'^\d+$')
    )

    PARENT = 'ganpatrimoine'
    BROWSER = GroupamaBrowser

    def create_default_browser(self):
        return self.create_browser(
            'groupama',
            self.config['login'].get(),
            self.config['password'].get(),
            weboob=self.weboob
        )

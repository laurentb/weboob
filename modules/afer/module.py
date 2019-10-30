# -*- coding: utf-8 -*-

# Copyright(C) 2015      James GALT
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

from weboob.capabilities.bank import CapBankWealth
from weboob.tools.backend import AbstractModule

from .browser import AferBrowser


__all__ = ['AferModule']


class AferModule(AbstractModule, CapBankWealth):
    NAME = 'afer'
    DESCRIPTION = "Association française d'épargne et de retraite"
    MAINTAINER = 'Quentin Defenouillère'
    EMAIL = 'quentin.defenouillere@budget-insight.com'
    LICENSE = 'LGPLv3+'
    VERSION = '1.6'

    PARENT = 'aviva'
    BROWSER = AferBrowser

    def create_default_browser(self):
        return self.create_browser(
            self.config['login'].get(),
            self.config['password'].get(),
            weboob=self.weboob
        )

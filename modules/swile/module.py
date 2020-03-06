# -*- coding: utf-8 -*-

# Copyright(C) 2018      Roger Philibert
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword
from weboob.capabilities.bank import CapBank

from .browser import SwileBrowser

__all__ = ['SwileModule']


class SwileModule(Module, CapBank):
    NAME = 'swile'
    DESCRIPTION = 'Swile'
    MAINTAINER = 'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    LICENSE = 'LGPLv3+'
    VERSION = '2.1'

    BROWSER = SwileBrowser

    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='E-mail', masked=False),
        ValueBackendPassword('password', label='Mot de passe'),
    )

    def create_default_browser(self):
        return self.create_browser(
            self.config['login'].get(),
            self.config['password'].get(),
        )

    def iter_accounts(self):
        return self.browser.get_account()

    def iter_history(self, account):
        return self.browser.iter_history(account)

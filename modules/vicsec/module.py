# -*- coding: utf-8 -*-

# Copyright(C) 2015      Oleg Plakhotniuk
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


from weboob.capabilities.shop import CapShop
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import VicSec


__all__ = ['VicSecModule']


class VicSecModule(Module, CapShop):
    NAME = 'vicsec'
    MAINTAINER = u'Oleg Plakhotniuk'
    EMAIL = 'olegus8@gmail.com'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Victoria\'s Secret'
    CONFIG = BackendConfig(
        ValueBackendPassword('email', label='Username', masked=False),
        ValueBackendPassword('password', label='Password'))
    BROWSER = VicSec

    def create_default_browser(self):
        return self.create_browser(self.config['email'].get(),
                                   self.config['password'].get())

    def get_currency(self):
        return self.browser.get_currency()

    def get_order(self, id_):
        return self.browser.get_order(id_)

    def iter_orders(self):
        return self.browser.iter_orders()

    def iter_payments(self, order):
        return self.browser.iter_payments(order)

    def iter_items(self, order):
        return self.browser.iter_items(order)

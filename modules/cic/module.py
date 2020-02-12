# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
# Copyright(C) 2012-2013 Romain Bignon
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

from weboob.capabilities.bank import CapBankTransferAddRecipient
from weboob.capabilities.contact import CapContact
from weboob.tools.backend import AbstractModule

from .browser import CICBrowser


__all__ = ['CICModule']


class CICModule(AbstractModule, CapBankTransferAddRecipient, CapContact):
    NAME = 'cic'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '2.1'
    DESCRIPTION = u'CIC'
    LICENSE = 'LGPLv3+'

    BROWSER = CICBrowser
    PARENT = 'creditmutuel'

    def create_default_browser(self):
        browser = self.create_browser(self.config, weboob=self.weboob)
        browser.new_accounts.urls.insert(0, "/mabanque/fr/banque/comptes-et-contrats.html")
        return browser

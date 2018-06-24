# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Julien Veyssier
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

from weboob.capabilities.bank import CapBankTransferAddRecipient
from weboob.capabilities.contact import CapContact
from weboob.tools.backend import AbstractModule, BackendConfig
from weboob.tools.value import ValueBackendPassword

from .browser import BECMBrowser


__all__ = ['BECMModule']


class BECMModule(AbstractModule, CapBankTransferAddRecipient, CapContact):
    NAME = 'becm'
    MAINTAINER = u'Victor Kannemacher'
    EMAIL = 'vkannemacher.budgetinsight@gmail.com'
    VERSION = '1.4'
    DESCRIPTION = u'Banque Europeenne Credit Mutuel'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'))
    BROWSER = BECMBrowser
    PARENT = 'creditmutuel'

    def create_default_browser(self):
        browser = self.create_browser(self.config['login'].get(), self.config['password'].get(), weboob=self.weboob)
        browser.new_accounts.urls.insert(0, "/mabanque/fr/banque/comptes-et-contrats.html")
        return browser

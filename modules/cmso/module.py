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


from weboob.capabilities.bank import CapBank, AccountNotFound
from weboob.capabilities.contact import CapContact
from weboob.capabilities.base import find_object
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .par.browser import CmsoParBrowser
from .pro.browser import CmsoProBrowser


__all__ = ['CmsoModule']


class CmsoModule(Module, CapBank, CapContact):
    NAME = 'cmso'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.4'
    DESCRIPTION = u'Crédit Mutuel Sud-Ouest'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(ValueBackendPassword('login',    label='Identifiant', masked=False),
                           ValueBackendPassword('password', label='Mot de passe'),
                           Value('website', label='Type de compte', default='par',
                                 choices={'par': 'Particuliers', 'pro': 'Professionnels'}))

    BROWSER = CmsoParBrowser

    def create_default_browser(self):
        b = {'par': CmsoParBrowser, 'pro': CmsoProBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser("%s.%s" % (self.NAME, 'com' if self.NAME == 'cmso' else 'fr'),
                                   self.config['login'].get(),
                                   self.config['password'].get())

    def get_account(self, _id):
        return find_object(self.browser.iter_accounts(), id=_id, error=AccountNotFound)

    def iter_accounts(self):
        return self.browser.iter_accounts()

    def iter_history(self, account):
        return self.browser.iter_history(account)

    def iter_coming(self, account):
        return self.browser.iter_coming(account)

    def iter_investment(self, account):
        return self.browser.iter_investment(account)

    def iter_contacts(self):
        if self.config['website'].get() != "par":
            raise NotImplementedError()

        return self.browser.get_advisor()

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Jocelyn Jaubert
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


from weboob.capabilities.bank import ICapBank, AccountNotFound
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .browser import SocieteGenerale
from .sgpe.browser import SGEnterpriseBrowser, SGProfessionalBrowser


__all__ = ['SocieteGeneraleBackend']


class SocieteGeneraleBackend(BaseBackend, ICapBank):
    NAME = 'societegenerale'
    MAINTAINER = u'Jocelyn Jaubert'
    EMAIL = 'jocelyn.jaubert@gmail.com'
    VERSION = '0.j'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'Société Générale'
    CONFIG = BackendConfig(
        ValueBackendPassword('login',      label='Code client', masked=False),
        ValueBackendPassword('password',   label='Code secret'),
        Value('website', label='Type de compte', default='par',
              choices={'par': 'Particuliers', 'pro': 'Professionnels', 'ent': 'Entreprises'}))

    def create_default_browser(self):
        b = {'par': SocieteGenerale, 'pro': SGProfessionalBrowser, 'ent': SGEnterpriseBrowser}
        self.BROWSER = b[self.config['website'].get()]
        return self.create_browser(self.config['login'].get(),
                                   self.config['password'].get())

    def iter_accounts(self):
        for account in self.browser.get_accounts_list():
            yield account

    def get_account(self, _id):
        with self.browser:
            account = self.browser.get_account(_id)
        if account:
            return account
        else:
            raise AccountNotFound()

    def iter_history(self, account):
        with self.browser:
            for tr in self.browser.iter_history(account):
                if not tr._coming:
                    yield tr

    def iter_coming(self, account):
        with self.browser:
            for tr in self.browser.iter_history(account):
                if tr._coming:
                    yield tr

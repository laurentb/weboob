# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Christophe Benz
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




from weboob.capabilities.messages import CantSendMessage, ICapMessages, ICapMessagesPost
from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.tools.value import ValueBackendPassword, Value

from .browser import BouyguesBrowser


__all__ = ['BouyguesBackend']


class BouyguesBackend(BaseBackend, ICapMessages, ICapMessagesPost):
    NAME = 'bouygues'
    MAINTAINER = u'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.j'
    DESCRIPTION = u'Bouygues Télécom French mobile phone provider'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login', label='Login'),
                           ValueBackendPassword('password', label='Password'))
    BROWSER = BouyguesBrowser
    ACCOUNT_REGISTER_PROPERTIES = None

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    def post_message(self, message):
        if not message.content.strip():
            raise CantSendMessage(u'Message content is empty.')
        with self.browser:
            self.browser.post_message(message)

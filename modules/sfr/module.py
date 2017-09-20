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


from weboob.capabilities.messages import CantSendMessage, CapMessages, CapMessagesPost
from weboob.capabilities.account import CapAccount, StatusField
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword

from .browser import SfrBrowser


__all__ = ['SfrModule']


class SfrModule(Module, CapAccount, CapMessages, CapMessagesPost):
    NAME = 'sfr'
    MAINTAINER = u'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '1.4'
    DESCRIPTION = 'SFR French mobile phone provider'
    LICENSE = 'AGPLv3+'
    CONFIG = BackendConfig(Value('login', label='Login'),
                           ValueBackendPassword('password', label='Password'))
    BROWSER = SfrBrowser
    ACCOUNT_REGISTER_PROPERTIES = None

    def create_default_browser(self):
        return self.create_browser(self.config['login'].get(), self.config['password'].get())

    # CapMessagesPost methods

    def get_account_status(self):
        with self.browser:
            return (StatusField('nb_remaining_free_sms', 'Number of remaining free SMS',
                                self.browser.get_nb_remaining_free_sms()),)

    def post_message(self, message):
        if not message.content.strip():
            raise CantSendMessage(u'Message content is empty.')
        with self.browser:
            self.browser.post_message(message)

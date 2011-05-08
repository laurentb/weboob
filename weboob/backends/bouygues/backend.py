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


from __future__ import with_statement

from weboob.capabilities.messages import CantSendMessage, ICapMessages, ICapMessagesPost
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import BouyguesBrowser


__all__ = ['BouyguesBackend']


class BouyguesBackend(BaseBackend, ICapMessages, ICapMessagesPost):
    NAME = 'bouygues'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.9'
    DESCRIPTION = 'Bouygues french mobile phone provider'
    LICENSE = 'AGPLv3+'
    CONFIG = ValuesDict(Value('login', label='Login'),
                        Value('password', label='Password', masked=True))
    BROWSER = BouyguesBrowser
    ACCOUNT_REGISTER_PROPERTIES = None

    def create_default_browser(self):
        return self.create_browser(self.config['login'], self.config['password'])

    def post_message(self, message):
        if not message.content.strip():
            raise CantSendMessage(u'Message content is empty.')
        with self.browser:
            self.browser.post_message(message)

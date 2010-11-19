# -*- coding: utf-8 -*-

# Copyright(C) 2010  Christophe Benz
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


from __future__ import with_statement

from weboob.capabilities.messages import ICapMessagesPost
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import SfrBrowser


__all__ = ['SfrBackend']


class SfrBackend(BaseBackend, ICapMessagesPost):
    NAME = 'sfr'
    MAINTAINER = 'Christophe Benz'
    EMAIL = 'christophe.benz@gmail.com'
    VERSION = '0.4'
    DESCRIPTION = 'SFR french mobile phone provider'
    LICENSE = 'GPLv3'
    CONFIG = ValuesDict(Value('login', label='Login'),
                        Value('password', label='Password', masked=True))
    BROWSER = SfrBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['login'], self.config['password'])

    # ICapMessagesPost methods

    def post_message(self, message):
        self.browser.post_message(message)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Nicolas Duhamel
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

from weboob.tools.backend import BaseBackend
from weboob.tools.value import Value, ValueBool, ValuesDict

from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread, CantSendMessage
from weboob.capabilities.collection import ICapCollection

from .browser import Downparadise

class DownparadiseBackend(BaseBackend, ICapCollection, ICapMessages, ICapMessagesPost):
    NAME = 'downparadise'
    MAINTAINER = 'Nicolas Duhamel'
    EMAIL = 'nicolas@jombi.fr'
    VERSION = '0.8'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = "Downparadise message board"

    CONFIG = ValuesDict(Value('username',          label='Username', regexp='.+'),
                        Value('password',          label='Password', regexp='.+', masked=True))

    BROWSER = Downparadise

    def create_default_browser(self):
        return self.create_browser(self.config['username'], self.config['password'])

    #############################
    ##  Collection

    def iter_resources(self, splited_path):
        return self.browser.iter_forums(splited_path)

    #############################
    ##  Messages

    def iter_threads(self):
        """
        Iterates on threads, from newers to olders.

        @return [iter]  Thread objects
        """
        raise NotImplementedError()

    def get_thread(self, id):
        """
        Get a specific thread.

        @return [Thread]  the Thread object
        """
        raise NotImplementedError()

    def iter_unread_messages(self, thread=None):
        """
        Iterates on messages which hasn't been marked as read.

        @param thread  thread name (optional)
        @return [iter]  Message objects
        """
        raise NotImplementedError()

    def set_message_read(self, message):
        """
        Set a message as read.

        @param [message]  message read (or ID)
        """
        raise NotImplementedError()

    #############################
    ##  Message Post

    def post_message(self, message):
        """
        Post a message.

        @param message  Message object
        @return
        """
        raise NotImplementedError()

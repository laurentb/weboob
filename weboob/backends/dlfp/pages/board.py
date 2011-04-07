# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
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

from weboob.tools.parsers.lxmlparser import select
from weboob.tools.browser import BasePage

class Message(object):
    def __init__(self, id, timestamp, login, message, is_me):
        self.id = id
        self.timestamp = timestamp
        self.login = login
        self.message = message
        self.is_me = is_me

class BoardIndexPage(BasePage):
    def is_logged(self):
        return True

    def get_messages(self, last=None):
        msgs = []
        for post in select(self.document.getroot(), 'post'):
            m = Message(int(post.attrib['id']),
                        post.attrib['time'],
                        post.find('login').text,
                        post.find('message').text,
                        post.find('login').text.lower() == self.browser.username.lower())
            if last is not None and last == m.id:
                break
            msgs.append(m)
        return msgs

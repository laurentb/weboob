# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011  Romain Bignon
#
# This file is part of a weboob module.
#
# This weboob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This weboob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this weboob module. If not, see <http://www.gnu.org/licenses/>.


import re
from logging import warning

from weboob.browser.pages import HTMLPage, LoggedPage


class Message(object):
    TIMESTAMP_REGEXP = re.compile(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})')

    def __init__(self, id, timestamp, login, message, is_me):
        self.id = id
        self.timestamp = timestamp
        self.login = login
        self.message = message
        self.is_me = is_me
        self.norloge = timestamp
        m = self.TIMESTAMP_REGEXP.match(timestamp)
        if m:
            self.norloge = '%02d:%02d:%02d' % (int(m.group(4)),
                                               int(m.group(5)),
                                               int(m.group(6)))
        else:
            warning('Unable to parse timestamp "%s"' % timestamp)


class BoardIndexPage(LoggedPage, HTMLPage):
    def get_messages(self, last=None):
        msgs = []
        for post in self.doc.xpath('//post'):
            m = Message(int(post.attrib['id']),
                        post.attrib['time'],
                        post.find('login').text,
                        post.find('message').text,
                        post.find('login').text.lower() == self.browser.username.lower())
            if last is not None and last == m.id:
                break
            msgs.append(m)
        return msgs

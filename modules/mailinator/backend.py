# -*- coding: utf-8 -*-

# Copyright(C) 2013      Vincent A
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


from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.messages import CapMessages, Thread, Message
from weboob.tools.value import Value

from .browser import MailinatorBrowser


__all__ = ['MailinatorBackend']


# There is only one thread per inbox, and the thread id is the inbox name
# TODO but this can lead to bans if there are too many messages...
class MailinatorBackend(BaseBackend, CapMessages):
    NAME = 'mailinator'
    DESCRIPTION = u'mailinator temp mailbox'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '0.j'

    BROWSER = MailinatorBrowser

    CONFIG = BackendConfig(Value('inbox', label='Inbox', default=''))

    def iter_threads(self):
        inbox = self.config['inbox'].get()
        if not inbox:
            raise NotImplementedError()
        else:
            return [self.get_thread(inbox)]

    def get_thread(self, _id):
        t = Thread(_id)
        t.title = 'Mail for %s' % _id
        t.flags = t.IS_DISCUSSION

        first = True
        for d in self.browser.get_mails(_id):
            m = self.make_message(d, t)
            if not m.content:
                m.content = self.browser.get_mail_content(m.id)

            if first:
                first = False
                t.root = m
            else:
                m.parent = t.root
                m.parent.children.append(m)

        return t

    def make_message(self, d, thread):
        m = Message(thread, d['id'])
        m.children = []
        m.sender = d['from']
        m.flags = 0
        if not d.get('read', True):
            m.flags = m.IS_UNREAD
        m.title = d['subject']
        m.date = d['datetime']
        m.receivers = [d['to']]
        return m

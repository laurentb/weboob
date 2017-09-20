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


from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.messages import CapMessages, Thread, Message
from weboob.tools.value import Value

from .browser import MailinatorBrowser


__all__ = ['MailinatorModule']


# There is only one thread per inbox, and the thread id is the inbox name
# TODO but this can lead to bans if there are too many messages...
class MailinatorModule(Module, CapMessages):
    NAME = 'mailinator'
    DESCRIPTION = u'mailinator temp mailbox'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    BROWSER = MailinatorBrowser

    CONFIG = BackendConfig(Value('inbox', label='Inbox', default=''))

    def iter_threads(self):
        inbox = self.config['inbox'].get()
        if not inbox:
            raise NotImplementedError()
        else:
            for d in self.browser.get_mails(inbox):
                thread = Thread(d['id'])
                thread.title = d['subject']
                thread.flags = thread.IS_DISCUSSION

                msg = self.make_message(d, thread)
                if not msg.content:
                    self._fetch_content(msg)

                thread.root = msg
                yield thread

    def _fetch_content(self, msg):
        msg_type, msg.content = self.browser.get_mail_content(msg.id)
        if msg_type == 'html':
            msg.flags = Message.IS_HTML

    def _get_messages_thread(self, inbox, thread):
        first = True
        for d in self.browser.get_mails(inbox):
            msg = self.make_message(d, thread)

            if first:
                first = False
                thread.root = msg
            else:
                msg.parent = thread.root
                msg.parent.children.append(msg)

    def get_thread(self, _id):
        thread = Thread(_id)
        thread.title = 'Mail for %s' % _id
        thread.flags = thread.IS_DISCUSSION

        self._get_messages_thread(_id, thread)
        return thread

    def make_message(self, d, thread):
        msg = Message(thread, d['id'])
        msg.children = []
        msg.sender = d['from']
        msg.flags = 0
        msg.title = d['subject']
        msg.date = d['datetime']
        msg.receivers = [d['to']]
        return msg

    def fill_msg(self, msg, fields):
        if 'content' in fields:
            self._fetch_content(msg)

        return msg

    OBJECTS = {Message: fill_msg}

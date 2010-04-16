# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Romain Bignon

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from weboob.backend import BaseBackend
from weboob.capabilities.messages import ICapMessages, ICapMessagesReply
from weboob.capabilities.dating import ICapDating
from weboob.tools.browser import BrowserUnavailable

from .browser import AdopteUnMec
from .optim.profiles_walker import ProfilesWalker

class AuMBackend(BaseBackend, ICapMessages, ICapMessagesReply, ICapDating):
    NAME = 'aum'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '1.0'
    LICENSE = 'GPLv3'
    DESCRIPTION = "French dating website"
    CONFIG = {'username':      BaseBackend.ConfigField(description='Username on website'),
              'password':      BaseBackend.ConfigField(description='Password of account', is_masked=True),
             }
    STORAGE = {'profiles_walker': {'viewed': []} }

    # Private
    _browser = None
    _profiles_walker = None

    def __getattr__(self, name):
        if name == 'browser':
            if not self._browser:
                self._browser = AdopteUnMec(self.config['username'], self.config['password'])
            return self._browser
        if name == 'queue_messages':
            if not hasattr(self, '_queue_messages'):
                self._queue_messages = []
            return self._queue_messages
        raise AttributeError, name

    def iter_messages(self, thread=None):
        for message in self._iter_messages(thread, False):
            yield message

    def iter_new_messages(self, thread=None):
        for message in self.queue_messages:
            if not thread or message.get_thread_id() == thread:
                yield message
        self.queue_messages = []

        for message in self._iter_messages(thread, True):
            yield message

    def _iter_messages(self, thread, only_new):
        try:
            if not only_new or self.browser.nb_new_mails():
                my_name = self.browser.get_my_name()
                contacts = self.browser.get_contact_list()
                contacts.reverse()

                for contact in contacts:
                    if only_new and not contact.is_new() or thread and int(thread) != contact.get_id():
                        continue

                    mails = self.browser.get_thread_mails(contact.get_id())
                    profile = None
                    for i in xrange(len(mails)):
                        mail = mails[i]
                        if only_new and mail.get_from() == my_name:
                            break

                        if not profile:
                            profile = self.browser.get_profile(contact.get_id())
                        mail.signature += u'\n%s' % profile.get_profile_text()
                        yield mail
        except BrowserUnavailable:
            pass

    def post_reply(self, thread_id, reply_id, title, message):
        for message in self._iter_messages(thread_id, True):
            self.queue_messages.append(message)
        return self.browser.post(thread_id, message)

    def get_profile(self, _id):
        try:
            return self.browser.get_profile(_id)
        except BrowserUnavailable:
            return None

    def start_profiles_walker(self):
        self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

    def stop_profiles_walker(self):
        self._profiles_walker.stop()
        self._profiles_walker = None

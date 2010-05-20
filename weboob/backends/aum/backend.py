# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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

from datetime import datetime
from dateutil import tz

from weboob.backend import BaseBackend
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.messages import ICapMessages, ICapMessagesReply, Message
from weboob.capabilities.dating import ICapDating
from weboob.tools.browser import BrowserUnavailable

from .browser import AdopteUnMec
from .exceptions import AdopteCantPostMail
from .optim.profiles_walker import ProfilesWalker


__all__ = ['AuMBackend']


class AuMBackend(BaseBackend, ICapMessages, ICapMessagesReply, ICapDating, ICapChat):
    NAME = 'aum'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '1.0'
    LICENSE = 'GPLv3'
    DESCRIPTION = "French dating website"
    CONFIG = {'username':      BaseBackend.ConfigField(description='Username on website'),
              'password':      BaseBackend.ConfigField(description='Password of account', is_masked=True),
             }
    STORAGE = {'profiles_walker': {'viewed': []},
               'sluts': {},
              }
    BROWSER = AdopteUnMec

    def default_browser(self):
        return self.build_browser(self.config['username'], self.config['password'])

    # Private
    _profiles_walker = None

    def iter_messages(self, thread=None):
        for message in self._iter_messages(thread, False):
            yield message

    def iter_new_messages(self, thread=None):
        for message in self._iter_messages(thread, True):
            yield message

    def _iter_messages(self, thread, only_new):
        with self.browser:
            try:
                profiles = {}

                contacts = self.browser.get_contact_list()
                for contact in contacts:
                    if not contact.get_id() in self.storage.get('sluts'):
                        slut = {'lastmsg': datetime(1970,1,1),
                                'msgstatus': ''}
                    else:
                        slut = self.storage.get('sluts', contact.get_id())

                    last_msg = slut['lastmsg'].replace(tzinfo=tz.tzutc())
                    new_lastmsg = last_msg

                    if only_new and contact.get_lastmsg_date() < last_msg and contact.get_status() == slut['msgstatus'] or \
                       not thread is None and int(thread) != contact.get_id():
                        continue

                    mails = self.browser.get_thread_mails(contact.get_id())
                    for mail in mails:
                        if only_new and mail.get_date() <= last_msg:
                            continue

                        if not mail.profile_link in profiles:
                            profiles[mail.profile_link] = self.browser.get_profile(mail.profile_link)
                        mail.signature += u'\n%s' % profiles[mail.profile_link].get_profile_text()

                        if new_lastmsg < mail.get_date():
                            new_lastmsg = mail.get_date()

                        yield mail

                    slut['lastmsg'] = new_lastmsg
                    slut['msgstatus'] = contact.get_status()
                    self.storage.set('sluts', contact.get_id(), slut)
                    self.storage.save()
            except BrowserUnavailable:
                pass

    def post_reply(self, thread_id, reply_id, title, message):
        with self.browser:
            self.browser.post_mail(thread_id, message)

    def get_profile(self, _id):
        try:
            with self.browser:
                return self.browser.get_profile(_id)
        except BrowserUnavailable:
            return None

    def start_profiles_walker(self):
        self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

    def stop_profiles_walker(self):
        if self._profiles_walker:
            self._profiles_walker.stop()
            self._profiles_walker = None

    def iter_chat_contacts(self, online=True, offline=True):
        return self.browser.iter_chat_contacts(online=online, offline=offline)

    def iter_chat_messages(self, _id=None):
        return self.browser.iter_chat_messages(_id)

    def send_chat_message(self, _id, message):
        return self.browser.send_chat_message(_id, message)

    #def start_chat_polling(self):
        #self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

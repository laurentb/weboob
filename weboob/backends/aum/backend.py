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
import os
from logging import warning
from time import sleep

from weboob.capabilities.chat import ICapChat
from weboob.capabilities.messages import ICapMessages, ICapMessagesReply, Message
from weboob.capabilities.dating import ICapDating, StatusField
from weboob.capabilities.contact import ICapContact, Contact, ProfileNode
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BrowserUnavailable

from .browser import AuMBrowser
from .exceptions import AdopteWait
from .optim.profiles_walker import ProfilesWalker
from .optim.visibility import Visibility


__all__ = ['AuMBackend']


class AuMBackend(BaseBackend, ICapMessages, ICapMessagesReply, ICapDating, ICapChat, ICapContact):
    NAME = 'aum'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@peerfuse.org'
    VERSION = '0.1'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"“Adopte un mec” french dating website"
    ICON = os.path.join(os.path.dirname(__file__), 'data/logo.png')
    CONFIG = {'username':      BaseBackend.ConfigField(description='Username on website'),
              'password':      BaseBackend.ConfigField(description='Password of account', is_masked=True),
              'register':      BaseBackend.ConfigField(default=False, description='Register as new account?'),
             }
    STORAGE = {'profiles_walker': {'viewed': []},
               'sluts': {},
              }
    BROWSER = AuMBrowser

    def create_default_browser(self):
        if self.config['register']:
            browser = self.create_browser(self.config['username'])
            browser.register(password=   self.config['password'],
                             sex=        0,
                             birthday_d= 1,
                             birthday_m= 1,
                             birthday_y= 1970,
                             zipcode=    75001,
                             country=    'fr',
                             godfather=  '')
        else:
            return self.create_browser(self.config['username'], self.config['password'])

    def get_status(self):
        with self.browser:
            try:
                return (
                        StatusField('myname', 'My name', self.browser.get_my_name()),
                        StatusField('score', 'Score', self.browser.score()),
                        StatusField('avcharms', 'Available charms', self.browser.nb_available_charms()),
                       )
            except AdopteWait:
                return (StatusField('notice', '', u'<h3>You are currently waiting 1am to be able to connect with this account</h3>', StatusField.FIELD_HTML|StatusField.FIELD_TEXT))

    def iter_messages(self, thread=None):
        for message in self._iter_messages(thread, False):
            yield message

    def iter_new_messages(self, thread=None):
        for message in self._iter_messages(thread, True):
            yield message

    def _get_slut(self, id):
        if not id in self.storage.get('sluts'):
            slut = {'lastmsg': datetime(1970,1,1),
                    'msgstatus': ''}
        else:
            slut = self.storage.get('sluts', id)

        slut['lastmsg'] = slut['lastmsg'].replace(tzinfo=tz.tzutc())
        return slut

    def _iter_messages(self, thread, only_new):
        with self.browser:
            try:
                profiles = {}

                if thread:
                    slut = self._get_slut(int(thread))
                    for mail in self._iter_thread_messages(thread, only_new, slut['lastmsg'], {}):
                        if slut['lastmsg'] < mail.get_date():
                            slut['lastmsg'] = mail.get_date()
                        yield mail

                    self.storage.set('sluts', int(thread), slut)
                    self.storage.save()
                else:
                    contacts = self.browser.get_threads_list()
                    for contact in contacts:
                        slut = self._get_slut(contact.get_id())
                        last_msg = slut['lastmsg']

                        if only_new and contact.get_lastmsg_date() < last_msg and contact.get_status() == slut['msgstatus'] or \
                           not thread is None and int(thread) != contact.get_id():
                            continue

                        for mail in self._iter_thread_messages(contact.get_id(), only_new, last_msg, profiles):
                            if last_msg < mail.get_date():
                                last_msg = mail.get_date()

                            yield mail

                        slut['lastmsg'] = last_msg
                        slut['msgstatus'] = contact.get_status()
                        self.storage.set('sluts', contact.get_id(), slut)
                        self.storage.save()

                    # Send mail when someone added me in her basket.
                    # XXX possibly race condition if a slut adds me in her basket
                    #     between the aum.nbNewBaskets() and aum.getBaskets().
                    new_baskets = self.browser.nb_new_baskets()
                    if new_baskets:
                        ids = self.browser.get_baskets()
                        while new_baskets > 0 and len(ids) > new_baskets:
                            new_baskets -= 1
                            profile = self.browser.get_profile(ids[new_baskets])

                            yield Message(profile.get_id(), 1,
                                          title='Basket of %s' % profile.get_name(),
                                          sender=profile.get_name(),
                                          content='You are taken in her basket!',
                                          signature=profile.get_profile_text())
            except BrowserUnavailable:
                pass

    def _iter_thread_messages(self, id, only_new, last_msg, profiles):
        mails = self.browser.get_thread_mails(id)
        for mail in mails:
            if only_new and mail.get_date() <= last_msg:
                continue

            if not mail.profile_link in profiles:
                profiles[mail.profile_link] = self.browser.get_profile(mail.profile_link)
            mail.signature += u'\n%s' % profiles[mail.profile_link].get_profile_text()

            yield mail

    def post_reply(self, thread_id, reply_id, title, message):
        while 1:
            try:
                with self.browser:
                    self.browser.post_mail(thread_id, message)
            except AdopteWait:
                # If we are on a waiting state, retry every 30 minutes until it is posted.
                sleep(60*30)
            else:
                return

    def get_contact(self, _id):
        try:
            with self.browser:
                profile = self.browser.get_profide(_id)

                if profile.is_online():
                    s = Contact.STATUS_ONLINE
                else:
                    s = Contact.STATUS_OFFLINE
                contact = Contact(_id, profile.get_name(), s)
                contact.status_msg = u'%s old' % profile.table['details']['old']
                contact.summary = profile.description
                contact.avatar = None
                contact.photos = profile.photos
                contact.profile = []

                stats = ProfileNode('stats', 'Stats', [], flags=ProfileNode.HEAD|ProfileNode.SECTION)
                for label, value in self.get_stats().iteritems():
                    stats.value.append(ProfileNode(label, label.capitalize(), value))
                contact.profile.append(stats)

                for section, d in self.get_table().iteritems():
                    s = ProfileNode(section, section.capitalize(), [], flags=ProfileNode.SECTION)
                    for key, value in d.iteritems():
                        s.value.append(ProfileNode(key, key.capitalize(), value))
        except BrowserUnavailable:
            return None

    def init_optimizations(self):
        self.OPTIM_PROFILE_WALKER = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)
        self.OPTIM_VISIBILITY = Visibility(self.weboob.scheduler, self.browser)

    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        with self.browser:
            for contact in self.browser.iter_contacts():
                s = 0
                if contact['cat'] == 1:
                    s = Contact.STATUS_ONLINE
                elif contact['cat'] == 3:
                    s = Contact.STATUS_OFFLINE
                elif contact['cat'] == 2:
                    s = Contact.STATUS_AWAY
                else:
                    warning('Unknown AuM contact status: %s' % contact['cat'])

                if not status & s or ids and contact['id'] in ids:
                    continue

                # TODO age in contact['birthday']
                c = Contact(contact['id'], contact['pseudo'], s)
                c.status_msg = u'%s old' % contact['birthday']
                c.thumbnail_url = contact['cover']
                yield c

    def iter_chat_messages(self, _id=None):
        with self.browser:
            return self.browser.iter_chat_messages(_id)

    def send_chat_message(self, _id, message):
        with self.browser:
            return self.browser.send_chat_message(_id, message)

    #def start_chat_polling(self):
        #self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

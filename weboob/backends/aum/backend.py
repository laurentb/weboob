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

import email
import re
import datetime
from dateutil import tz

from weboob.capabilities.base import NotLoaded
from weboob.capabilities.chat import ICapChat
from weboob.capabilities.messages import ICapMessages, ICapMessagesPost, Message, Thread
from weboob.capabilities.dating import ICapDating, OptimizationNotFound
from weboob.capabilities.contact import ICapContact, Contact, ContactPhoto, ProfileNode, Query, QueryError
from weboob.capabilities.account import ICapAccount, StatusField
from weboob.tools.backend import BaseBackend
from weboob.tools.browser import BrowserUnavailable
from weboob.tools.value import Value, ValuesDict, ValueBool
from weboob.tools.log import getLogger

from .captcha import CaptchaError
from .antispam import AntiSpam
from .browser import AuMBrowser
from .exceptions import AdopteWait
from .optim.profiles_walker import ProfilesWalker
from .optim.visibility import Visibility
from .optim.priority_connection import PriorityConnection
from .optim.queries_queue import QueriesQueue


__all__ = ['AuMBackend']


class AuMBackend(BaseBackend, ICapMessages, ICapMessagesPost, ICapDating, ICapChat, ICapContact, ICapAccount):
    NAME = 'aum'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.4'
    LICENSE = 'GPLv3'
    DESCRIPTION = u"“Adopte un mec” french dating website"
    CONFIG = ValuesDict(Value('username',     label='Username'),
                        Value('password',     label='Password', masked=True),
                        ValueBool('antispam', label='Enable anti-spam', default=False),
                        ValueBool('baskets',  label='Get baskets with new messages', default=True))
    STORAGE = {'profiles_walker': {'viewed': []},
               'priority_connection': {'config': {}, 'fakes': {}},
               'queries_queue': {'queue': []},
               'sluts': {},
              }
    BROWSER = AuMBrowser

    MAGIC_ID_BASKET = 1

    def __init__(self, *args, **kwargs):
        BaseBackend.__init__(self, *args, **kwargs)
        if self.config['antispam']:
            self.antispam = AntiSpam()
        else:
            self.antispam = None

    def create_default_browser(self):
        return self.create_browser(self.config['username'], self.config['password'])

    def report_spam(self, id, suppr_id=None):
        if suppr_id:
            self.browser.delete_thread(suppr_id)
        self.browser.report_fake(id)
        pass

    # ---- ICapDating methods ---------------------

    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))
        self.add_optimization('VISIBILITY', Visibility(self.weboob.scheduler, self.browser))
        self.add_optimization('PRIORITY_CONNECTION', PriorityConnection(self.weboob.scheduler, self.storage, self.browser))
        self.add_optimization('QUERIES_QUEUE', QueriesQueue(self.weboob.scheduler, self.storage, self.browser))

    # ---- ICapMessages methods ---------------------

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        with self.browser:
            contacts = self.browser.get_threads_list()

        for contact in contacts:
            if not contact.get_id():
                continue
            if self.antispam and not self.antispam.check(contact):
                self.logger.info('Skipped a spam-thread from %s' % contact.get_name())
                self.report_spam(contact.get_id(), contact.get_suppr_id())
                continue
            thread = Thread(contact.get_id())
            thread.title = 'Discussion with %s' % contact.get_name()
            yield thread

    def get_thread(self, id, profiles=None, contact=None):
        """
        Get a thread and its messages.

        The 'profiles' and 'contact' parameters are only used for internal calls.
        """
        thread = None
        if isinstance(id, Thread):
            thread = id
            id = thread.id

        if not thread:
            thread = Thread(id)
            full = False
        else:
            full = True

        with self.browser:
            mails = self.browser.get_thread_mails(id, full)
            my_name = self.browser.get_my_name()

        child = None
        msg = None
        slut = self._get_slut(id)
        if not profiles:
            profiles = {}
        for mail in mails:
            flags = 0
            if self.antispam and not self.antispam.check(mail):
                self.logger.info('Skipped a spam-mail from %s' % mail.sender)
                self.report_spam(thread.id, contact and contact.get_suppr_id())
                break

            if mail.date > slut['lastmsg']:
                flags |= Message.IS_UNREAD

                if not mail.profile_link in profiles:
                    with self.browser:
                        profiles[mail.profile_link] = self.browser.get_profile(mail.profile_link)
                if self.antispam and not self.antispam.check(profiles[mail.profile_link]):
                    self.logger.info('Skipped a spam-mail-profile from %s' % mail.sender)
                    self.report_spam(thread.id, contact and contact.get_suppr_id())
                    break
                mail.signature += u'\n%s' % profiles[mail.profile_link].get_profile_text()

            if mail.sender == my_name:
                if mail.new:
                    flags |= Message.IS_NOT_ACCUSED
                else:
                    flags |= Message.IS_ACCUSED

            if not thread.title:
                thread.title = mail.title

            msg = Message(thread=thread,
                          id=mail.message_id,
                          title=mail.title,
                          sender=mail.sender,
                          receiver=mail.name if mail.sender == my_name else my_name, # TODO: me
                          date=mail.date,
                          content=mail.content,
                          signature=mail.signature,
                          children=[],
                          flags=flags)
            if child:
                msg.children.append(child)
                child.parent = msg

            child = msg

        if full and msg:
            # If we have get all the messages, replace NotLoaded with None as
            # parent.
            msg.parent = None
        if not full and not msg:
            # Perhaps there are hidden messages
            msg = NotLoaded

        thread.root = msg

        return thread

    def iter_unread_messages(self, thread=None):
        try:
            profiles = {}
            with self.browser:
                contacts = self.browser.get_threads_list()
            for contact in contacts:
                if not contact.get_id():
                    continue
                if self.antispam and not self.antispam.check(contact):
                    self.logger.info('Skipped a spam-unread-thread from %s' % contact.get_name())
                    self.report_spam(contact.get_id(), contact.get_suppr_id())
                    continue
                slut = self._get_slut(contact.get_id())
                if contact.get_lastmsg_date() > slut['lastmsg']:
                    thread = self.get_thread(contact.get_id(), profiles, contact)
                    for m in thread.iter_all_messages():
                        if m.flags & m.IS_UNREAD:
                            yield m

            if not self.config['baskets']:
                return

            # Send mail when someone added me in her basket.
            # XXX possibly race condition if a slut adds me in her basket
            #     between the aum.nb_new_baskets() and aum.get_baskets().
            with self.browser:
                new_baskets = self.browser.nb_new_baskets()
                if new_baskets:
                    ids = self.browser.get_baskets()
                    while new_baskets > 0 and len(ids) > new_baskets:
                        new_baskets -= 1
                        if ids[new_baskets] == '-1':
                            continue
                        profile = self.browser.get_profile(ids[new_baskets])
                        if not profile or profile.get_id() == 0:
                            continue
                        if self.antispam and not self.antispam.check(profile):
                            self.logger.info('Skipped a spam-basket from %s' % profile.get_name())
                            self.report_spam(profile.get_id())
                            continue

                        thread = Thread(profile.get_id())
                        thread.title = 'Basket of %s' % profile.get_name()
                        thread.root = Message(thread=thread,
                                              id=self.MAGIC_ID_BASKET,
                                              title=thread.title,
                                              sender=profile.get_name(),
                                              receiver=self.browser.get_my_name(),
                                              date=None, # now
                                              content='You are taken in her basket!',
                                              signature=profile.get_profile_text(),
                                              children=[],
                                              flags=Message.IS_UNREAD)
                        yield thread.root
        except BrowserUnavailable, e:
            self.logger.debug('No messages, browser is unavailable: %s' % e)
            pass # don't care about waiting

    def set_message_read(self, message):
        if message.id == self.MAGIC_ID_BASKET:
            # We don't save baskets.
            return

        slut = self._get_slut(message.thread.id)
        if slut['lastmsg'] < message.date:
            slut['lastmsg'] = message.date
            #slut['msgstatus'] = contact.get_status()
            self.storage.set('sluts', message.thread.id, slut)
            self.storage.save()

    def _get_slut(self, id):
        sluts = self.storage.get('sluts')
        if not sluts or not id in sluts:
            slut = {'lastmsg': datetime.datetime(1970,1,1),
                    'msgstatus': ''}
        else:
            slut = self.storage.get('sluts', id)

        slut['lastmsg'] = slut['lastmsg'].replace(tzinfo=tz.tzutc())
        return slut

    # ---- ICapMessagesPost methods ---------------------

    def post_message(self, message):
        with self.browser:
            self.browser.post_mail(message.thread.id, message.content)

    # ---- ICapContact methods ---------------------

    def fill_contact(self, contact, fields):
        if 'profile' in fields:
            contact = self.get_contact(contact)
        if contact and 'photos' in fields:
            for name, photo in contact.photos.iteritems():
                with self.browser:
                    if photo.url and not photo.data:
                        data = self.browser.openurl(photo.url).read()
                        contact.set_photo(name, data=data)
                    if photo.thumbnail_url and not photo.thumbnail_data:
                        data = self.browser.openurl(photo.thumbnail_url).read()
                        contact.set_photo(name, thumbnail_data=data)

    def fill_photo(self, photo, fields):
        with self.browser:
            if 'data' in fields and photo.url and not photo.data:
                photo.data = self.browser.readurl(photo.url)
            if 'thumbnail_data' in fields and photo.thumbnail_url and not photo.thumbnail_data:
                photo.thumbnail_data = self.browser.readurl(photo.thumbnail_url)
        return photo

    def get_contact(self, contact):
        with self.browser:
            if isinstance(contact, Contact):
                _id = contact.id
            elif isinstance(contact, (int,long,basestring)):
                _id = contact
            else:
                raise TypeError("The parameter 'contact' isn't a contact nor a int/long/str/unicode: %s" % contact)

            profile = self.browser.get_profile(_id)
            if not profile:
                return None

            _id = profile.id

            if profile.is_online():
                s = Contact.STATUS_ONLINE
            else:
                s = Contact.STATUS_OFFLINE

            if isinstance(contact, Contact):
                contact.id = _id
                contact.name = profile.get_name()
                contact.status = s
            else:
                contact = Contact(_id, profile.get_name(), s)
            contact.url = self.browser.id2url(_id)
            contact.status_msg = profile.get_status()
            contact.summary = profile.description
            for photo in profile.photos:
                contact.set_photo(photo['url'].split('/')[-1],
                                  url=photo['url'],
                                  thumbnail_url=photo['url'].replace('image', 'thumb1_'),
                                  hidden=photo['hidden'])
            contact.profile = []

            stats = ProfileNode('stats', 'Stats', [], flags=ProfileNode.HEAD|ProfileNode.SECTION)
            for label, value in profile.get_stats().iteritems():
                stats.value.append(ProfileNode(label, label.capitalize(), value))
            contact.profile.append(stats)

            for section, d in profile.get_table().iteritems():
                s = ProfileNode(section, section.capitalize(), [], flags=ProfileNode.SECTION)
                for key, value in d.iteritems():
                    s.value.append(ProfileNode(key, key.capitalize(), value))
                contact.profile.append(s)

            return contact

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
                    self.logger.warning('Unknown AuM contact status: %s' % contact['cat'])

                if not status & s or ids and contact['id'] in ids:
                    continue

                # TODO age in contact['birthday']
                c = Contact(contact['id'], contact['pseudo'], s)
                c.url = self.browser.id2url(contact['id'])
                c.status_msg = u'%s old' % contact['birthday']
                c.set_photo(contact['cover'].split('/')[-1].replace('thumb0_', 'image'),
                            url=contact['cover'].replace('thumb0_', 'image'),
                            thumbnail_url=contact['cover'])
                yield c

    def send_query(self, id):
        if isinstance(id, Contact):
            id = id.id

        queries_queue = None
        try:
            queries_queue = self.get_optimization('QUERIES_QUEUE')
        except OptimizationNotFound:
            pass

        if queries_queue and queries_queue.is_running():
            if queries_queue.enqueue_query(id):
                return Query(id, 'A charm has been sent')
            else:
                return Query(id, 'Unable to send charm: it has been enqueued')
        else:
            with self.browser:
                if not self.browser.send_charm(id):
                    raise QueryError('No enough charms available')
                return Query(id, 'A charm has been sent')

    # ---- ICapChat methods ---------------------

    def iter_chat_messages(self, _id=None):
        with self.browser:
            return self.browser.iter_chat_messages(_id)

    def send_chat_message(self, _id, message):
        with self.browser:
            return self.browser.send_chat_message(_id, message)

    #def start_chat_polling(self):
        #self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

    # ---- ICapAccount methods ---------------------

    ACCOUNT_REGISTER_PROPERTIES = ValuesDict(
                Value('username', label='Email address', regexp='^[^ ]+@[^ ]+\.[^ ]+$'),
                Value('password', label='Password', regexp='^[^ ]+$', masked=True),
                Value('sex',      label='Sex', choices={'m': 'Male', 'f': 'Female'}),
                Value('birthday', label='Birthday (dd/mm/yyyy)', regexp='^\d+/\d+/\d+$'),
                Value('zipcode',  label='Zipcode'),
                Value('country',  label='Country', choices={'fr': 'France', 'be': 'Belgique', 'ch': 'Suisse', 'ca': 'Canada'}, default='fr'),
                Value('godfather',label='Godfather', regexp='^\d*$', default=''),
               )

    @classmethod
    def register_account(klass, account):
        """
        Register an account on website

        This is a static method, it would be called even if the backend is
        instancied.

        @param account  an Account object which describe the account to create
        """
        browser = None
        bday, bmonth, byear = account.properties['birthday'].value.split('/', 2)
        while not browser:
            try:
                browser = klass.BROWSER(account.properties['username'].value)
                browser.register(password=   account.properties['password'].value,
                                 sex=        (0 if account.properties['sex'].value == 'm' else 1),
                                 birthday_d= int(bday),
                                 birthday_m= int(bmonth),
                                 birthday_y= int(byear),
                                 zipcode=    account.properties['zipcode'].value,
                                 country=    account.properties['country'].value,
                                 godfather=  account.properties['godfather'].value)
            except CaptchaError:
                getLogger('aum').info('Unable to resolve captcha. Retrying...')
                browser = None

    REGISTER_REGEXP = re.compile('.*http://www.adopteunmec.com/register4.php\?([^\' ]*)\'')
    def confirm_account(self, mail):
        msg = email.message_from_string(mail)

        content = u''
        for part in msg.walk():
            s = part.get_payload(decode=True)
            content += unicode(s, 'iso-8859-15')

        url = None
        for s in content.split():
            m = self.REGISTER_REGEXP.match(s)
            if m:
                url = '/register4.php?' + m.group(1)
                break

        if url:
            browser = self.create_browser('')
            browser.openurl(url)
            return True

        return False

    def get_account(self):
        """
        Get the current account.
        """
        raise NotImplementedError()

    def update_account(self, account):
        """
        Update the current account.
        """
        raise NotImplementedError()

    def get_account_status(self):
        with self.browser:
            try:
                return (
                        StatusField('myname', 'My name', self.browser.get_my_name()),
                        StatusField('score', 'Score', self.browser.score()),
                        StatusField('avcharms', 'Available charms', self.browser.nb_available_charms()),
                        StatusField('godchilds', 'Number of godchilds', self.browser.nb_godchilds()),
                       )
            except AdopteWait:
                return (StatusField('notice', '', u'<h3>You are currently waiting 1am to be able to connect with this account</h3>', StatusField.FIELD_HTML|StatusField.FIELD_TEXT))

    OBJECTS = {Thread: fill_thread,
               Contact: fill_contact,
               ContactPhoto: fill_photo
              }

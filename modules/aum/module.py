# -*- coding: utf-8 -*-

# Copyright(C) 2010-2014 Romain Bignon
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


import time
import datetime
from base64 import b64decode
from html2text import unescape
from dateutil import tz
from dateutil.parser import parse as _parse_dt

from weboob.capabilities.base import NotLoaded
from weboob.capabilities.chat import CapChat
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message, Thread
from weboob.capabilities.dating import CapDating, OptimizationNotFound, Event
from weboob.capabilities.contact import CapContact, ContactPhoto, Query, QueryError
from weboob.capabilities.account import CapAccount, StatusField
from weboob.tools.backend import Module, BackendConfig
from weboob.exceptions import BrowserUnavailable, BrowserHTTPNotFound
from weboob.tools.value import Value, ValueBool, ValueBackendPassword
from weboob.tools.date import local2utc
from weboob.tools.misc import to_unicode
from weboob.tools.compat import unicode, long, basestring

from .contact import Contact
from .antispam import AntiSpam
from .browser import AuMBrowser
from .optim.profiles_walker import ProfilesWalker
from .optim.visibility import Visibility
from .optim.queries_queue import QueriesQueue


__all__ = ['AuMModule']


def parse_dt(s):
    d = _parse_dt(s)
    return local2utc(d)


class AuMModule(Module, CapMessages, CapMessagesPost, CapDating, CapChat, CapContact, CapAccount):
    NAME = 'aum'
    MAINTAINER = u'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'"Adopte un Mec" French dating website'
    CONFIG = BackendConfig(Value('username',                label='Username'),
                           ValueBackendPassword('password', label='Password'),
                           ValueBool('antispam',            label='Enable anti-spam', default=False),
                           ValueBool('baskets',             label='Get baskets with new messages', default=True),
                           Value('search_query',        label='Search query', default=''))
    STORAGE = {'profiles_walker': {'viewed': []},
               'queries_queue': {'queue': []},
               'contacts': {},
               'notes': {},
              }
    BROWSER = AuMBrowser

    MAGIC_ID_BASKET = 1

    def __init__(self, *args, **kwargs):
        Module.__init__(self, *args, **kwargs)
        if self.config['antispam'].get():
            self.antispam = AntiSpam()
        else:
            self.antispam = None

    def create_default_browser(self):
        return self.create_browser(self.config['username'].get(),
                                   self.config['password'].get(),
                                   self.config['search_query'].get())

    def report_spam(self, id):
        pass
        #self.browser.delete_thread(id)
        # Do not report fakes to website, to let them to other guys :)
        #self.browser.report_fake(id)

    # ---- CapDating methods ---------------------

    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))
        self.add_optimization('VISIBILITY', Visibility(self.weboob.scheduler, self.browser))
        self.add_optimization('QUERIES_QUEUE', QueriesQueue(self.weboob.scheduler, self.storage, self.browser))

    def iter_events(self):
        all_events = {}
        all_events[u'baskets'] = (self.browser.get_baskets, 'You were put into %s\'s basket')
        all_events[u'flashs'] =  (self.browser.get_flashs, 'You sent a charm to %s')
        all_events[u'visits'] =  (self.browser.get_visits, 'Visited by %s')
        for type, (events, message) in all_events.items():
            for event in events():
                e = Event(event['who']['id'])

                e.date = parse_dt(event['date'])
                e.type = type
                if 'who' in event:
                    e.contact = self._get_partial_contact(event['who'])
                else:
                    e.contact = self._get_partial_contact(event)

                if not e.contact:
                    continue

                e.message = message % e.contact.name
                yield e

    def iter_new_contacts(self):
        for _id in self.browser.search_profiles():#.difference(self.OPTIM_PROFILE_WALKER.visited_profiles):
            contact = Contact(_id, '', 0)
            yield contact

    # ---- CapMessages methods ---------------------

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        threads = self.browser.get_threads_list()

        for thread in threads:
            #if thread['member'].get('isBan', thread['member'].get('dead', False)):
            #    self.browser.delete_thread(thread['member']['id'])
            #    continue
            if self.antispam and not self.antispam.check_thread(thread):
                self.logger.info('Skipped a spam-thread from %s' % thread['pseudo'])
                self.report_spam(thread['who']['id'])
                continue
            t = Thread(int(thread['who']['id']))
            t.flags = Thread.IS_DISCUSSION
            t.title = u'Discussion with %s' % to_unicode(thread['who']['pseudo'])
            yield t

    def get_thread(self, id, contacts=None, get_profiles=False):
        """
        Get a thread and its messages.

        The 'contacts' parameters is only used for internal calls.
        """
        thread = None
        if isinstance(id, Thread):
            thread = id
            id = thread.id

        if not thread:
            thread = Thread(int(id))
            thread.flags = Thread.IS_DISCUSSION
            full = False
        else:
            full = True

        mails = self.browser.get_thread_mails(id, 100)
        my_name = self.browser.get_my_name()

        child = None
        msg = None
        contact = self._get_contact(id)
        if contacts is None:
            contacts = {}

        if not thread.title:
            thread.title = u'Discussion with %s' % mails['who']['pseudo']

        self.storage.set('contacts', int(thread.id), 'status', mails['status'])
        self.storage.save()

        for mail in mails['results']:
            flags = 0
            if self.antispam and not self.antispam.check_mail(mail):
                self.logger.info('Skipped a spam-mail from %s' % mails['who']['pseudo'])
                self.report_spam(thread.id)
                break

            if parse_dt(mail['date']) > contact['lastmsg']:
                flags |= Message.IS_UNREAD

                if get_profiles:
                    if mail['from'] not in contacts:
                        try:
                            contacts[mail['from']] = self.get_contact(mail['from'])
                        except BrowserHTTPNotFound:
                            pass
                    if self.antispam and mail['from'] in contacts and not self.antispam.check_contact(contacts[mail['from']]):
                        self.logger.info('Skipped a spam-mail-profile from %s' % mails['who']['pseudo'])
                        self.report_spam(thread.id)
                        break

            if int(mail['from']) == self.browser.my_id:
                if mails['remote_status'] == 'new' and msg is None:
                    flags |= Message.IS_NOT_RECEIVED
                else:
                    flags |= Message.IS_RECEIVED

            signature = u''
            #if mail.get('src', None):
            #    signature += u'Sent from my %s\n\n' % mail['src']
            if mail['from'] in contacts:
                signature += contacts[mail['from']].get_text()

            msg = Message(thread=thread,
                          id=int(time.strftime('%Y%m%d%H%M%S', parse_dt(mail['date']).timetuple())),
                          title=thread.title,
                          sender=to_unicode(my_name if int(mail['from']) == self.browser.my_id else mails['who']['pseudo']),
                          receivers=[to_unicode(my_name if int(mail['from']) != self.browser.my_id else mails['who']['pseudo'])],
                          date=parse_dt(mail['date']),
                          content=to_unicode(unescape(mail['message'] or '').strip()),
                          signature=signature,
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

    def iter_unread_messages(self):
        try:
            contacts = {}
            threads = self.browser.get_threads_list()
            for thread in threads:
                #if thread['member'].get('isBan', thread['member'].get('dead', False)):
                #    self.browser.delete_thread(int(thread['member']['id']))
                #    continue
                if self.antispam and not self.antispam.check_thread(thread):
                    self.logger.info('Skipped a spam-unread-thread from %s' % thread['who']['pseudo'])
                    self.report_spam(thread['member']['id'])
                    continue
                contact = self._get_contact(thread['who']['id'])
                if parse_dt(thread['date']) > contact['lastmsg'] or thread['status'] != contact['status']:
                    try:
                        t = self.get_thread(thread['who']['id'], contacts, get_profiles=True)
                    except BrowserUnavailable:
                        continue
                    for m in t.iter_all_messages():
                        if m.flags & m.IS_UNREAD:
                            yield m

            if not self.config['baskets'].get():
                return

            # Send mail when someone added me in her basket.
            # XXX possibly race condition if a contact adds me in her basket
            #     between the aum.nb_new_baskets() and aum.get_baskets().
            contact = self._get_contact(-self.MAGIC_ID_BASKET)

            new_baskets = self.browser.nb_new_baskets()
            if new_baskets > 0:
                baskets = self.browser.get_baskets()
                my_name = self.browser.get_my_name()
                for basket in baskets:
                    if parse_dt(basket['date']) <= contact['lastmsg']:
                        continue
                    contact = self.get_contact(basket['who']['id'])
                    if self.antispam and not self.antispam.check_contact(contact):
                        self.logger.info('Skipped a spam-basket from %s' % contact.name)
                        self.report_spam(basket['who']['id'])
                        continue

                    thread = Thread(int(basket['who']['id']))
                    thread.title = 'Basket of %s' % contact.name
                    thread.root = Message(thread=thread,
                                          id=self.MAGIC_ID_BASKET,
                                          title=thread.title,
                                          sender=contact.name,
                                          receivers=[my_name],
                                          date=parse_dt(basket['date']),
                                          content='You are taken in her basket!',
                                          signature=contact.get_text(),
                                          children=[],
                                          flags=Message.IS_UNREAD)
                    yield thread.root
        except BrowserUnavailable as e:
            self.logger.debug('No messages, browser is unavailable: %s' % e)
            pass  # don't care about waiting

    def set_message_read(self, message):
        if int(message.id) == self.MAGIC_ID_BASKET:
            # Save the last baskets checks.
            contact = self._get_contact(-self.MAGIC_ID_BASKET)
            if contact['lastmsg'] < message.date:
                contact['lastmsg'] = message.date
                self.storage.set('contacts', -self.MAGIC_ID_BASKET, contact)
                self.storage.save()
            return

        contact = self._get_contact(message.thread.id)
        if contact['lastmsg'] < message.date:
            contact['lastmsg'] = message.date
            self.storage.set('contacts', int(message.thread.id), contact)
            self.storage.save()

    def _get_contact(self, id):
        id = int(id)
        contacts = self.storage.get('contacts')
        if not contacts or id not in contacts:
            contacts = self.storage.get(b64decode('c2x1dHM='))
        if not contacts or id not in contacts:
            contact = {'lastmsg': datetime.datetime(1970,1,1),
                       'status':  None}
        else:
            contact = contacts[id]

        contact['lastmsg'] = contact.get('lastmsg', datetime.datetime(1970,1,1)).replace(tzinfo=tz.tzutc())
        contact['status'] = contact.get('status', None)
        return contact

    # ---- CapMessagesPost methods ---------------------

    def post_message(self, message):
        self.browser.post_mail(message.thread.id, message.content)

    # ---- CapContact methods ---------------------

    def fill_contact(self, contact, fields):
        if 'profile' in fields:
            contact = self.get_contact(contact)
        if contact and 'photos' in fields:
            for name, photo in contact.photos.items():
                if photo.url and not photo.data:
                    data = self.browser.openurl(photo.url).read()
                    contact.set_photo(name, data=data)
                if photo.thumbnail_url and not photo.thumbnail_data:
                    data = self.browser.openurl(photo.thumbnail_url).read()
                    contact.set_photo(name, thumbnail_data=data)

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        if 'thumbnail_data' in fields and photo.thumbnail_url and not photo.thumbnail_data:
            photo.thumbnail_data = self.browser.open(photo.thumbnail_url).content
        return photo

    def get_contact(self, contact):
        if isinstance(contact, Contact):
            _id = contact.id
        elif isinstance(contact, (int,long,basestring)):
            _id = contact
        else:
            raise TypeError("The parameter 'contact' isn't a contact nor a int/long/str/unicode: %s" % contact)

        profile = self.browser.get_full_profile(_id)
        if not profile:
            return None

        _id = profile['id']

        if isinstance(contact, Contact):
            contact.id = _id
            contact.name = profile['pseudo']
        else:
            contact = Contact(_id, profile['pseudo'], Contact.STATUS_ONLINE)
        contact.url = self.browser.id2url(_id)
        contact.parse_profile(profile, self.browser.get_consts())
        return contact

    def _get_partial_contact(self, contact):
        s = 0
        if contact.get('online', False):
            s = Contact.STATUS_ONLINE
        else:
            s = Contact.STATUS_OFFLINE

        c = Contact(contact['id'], to_unicode(contact['pseudo']), s)
        c.url = self.browser.id2url(contact['id'])
        if 'age' in contact:
            c.status_msg = u'%s old, %s' % (contact['age'], contact['city'])
        if contact['cover'] is not None:
            url = contact['cover'] + '/%(type)s'
        else:
            url = u'http://s.adopteunmec.com/www/img/thumb0.jpg'

        c.set_photo(u'image%s' % contact['cover'],
                    url=url % {'type': 'full'},
                    thumbnail_url=url % {'type': 'small'})
        return c

    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        threads = self.browser.get_threads_list(count=100)

        for thread in threads:
            c = self._get_partial_contact(thread['who'])
            if c and (c.status & status) and (not ids or c.id in ids):
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
            if not self.browser.send_charm(id):
                raise QueryError('No enough charms available')
            return Query(id, 'A charm has been sent')

    def get_notes(self, id):
        if isinstance(id, Contact):
            id = id.id

        return self.storage.get('notes', id)

    def save_notes(self, id, notes):
        if isinstance(id, Contact):
            id = id.id

        self.storage.set('notes', id, notes)
        self.storage.save()

    # ---- CapChat methods ---------------------

    def iter_chat_messages(self, _id=None):
        return self.browser.iter_chat_messages(_id)

    def send_chat_message(self, _id, message):
        return self.browser.send_chat_message(_id, message)

    #def start_chat_polling(self):
        #self._profile_walker = ProfilesWalker(self.weboob.scheduler, self.storage, self.browser)

    def get_account_status(self):
        return (
                StatusField(u'myname', u'My name', unicode(self.browser.get_my_name())),
                StatusField(u'score', u'Score', unicode(self.browser.score())),
                StatusField(u'avcharms', u'Available charms', unicode(self.browser.nb_available_charms())),
                StatusField(u'newvisits', u'New visits', unicode(self.browser.nb_new_visites())),
               )

    OBJECTS = {Thread: fill_thread,
               Contact: fill_contact,
               ContactPhoto: fill_photo
              }

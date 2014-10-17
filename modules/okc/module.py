# -*- coding: utf-8 -*-

# Copyright(C) 2012 Roger Philibert
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


import time
import datetime
from dateutil import tz
from dateutil.parser import parse as _parse_dt

from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message, Thread
from weboob.capabilities.dating import CapDating, OptimizationNotFound, Event
from weboob.capabilities.contact import CapContact, ContactPhoto, Contact, Query, QueryError
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.date import local2utc

from .browser import OkCBrowser
from .optim.profiles_walker import ProfilesWalker


__all__ = ['OkCModule']


def parse_dt(s):
    now = datetime.datetime.now()
    if s is None:
        return local2utc(now)
    if 'minutes ago' in s:
        m = int(s.split()[0])
        d = now - datetime.timedelta(minutes=m)
    elif u'–' in s:
        # Date in form : "Yesterday – 20:45"
        day, hour = s.split(u'–')
        day = day.strip()
        hour = hour.strip()
        if day == 'Yesterday':
            d = now - datetime.timedelta(days=1)
        elif day == 'Today':
            d = now
        hour = _parse_dt(hour)
        d = datetime.datetime(d.year, d.month, d.day, hour.hour, hour.minute)
    else:
        #if ',' in s:
        # Date in form : "Dec 28, 2011")
        d = _parse_dt(s)
    return local2utc(d)


class OkCModule(Module, CapMessages, CapContact, CapMessagesPost, CapDating):
    NAME = 'okc'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '1.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'OkCupid dating website'
    CONFIG = BackendConfig(Value('username',                label='Username'),
                           ValueBackendPassword('password', label='Password'))
    STORAGE = {'profiles_walker': {'viewed': []},
            'queries_queue': {'queue': []},
               'sluts': {},
               #'notes': {},
              }
    BROWSER = OkCBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['username'].get(), self.config['password'].get())

    # ---- CapDating methods ---------------------
    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))

    def iter_events(self):
        all_events = {}
        with self.browser:
            all_events[u'visits'] =  (self.browser.get_visits, 'Visited by %s')
        for type, (events, message) in all_events.iteritems():
            for event in events():
                e = Event(event['who']['id'])

                e.date = parse_dt(event['date'])
                e.type = type
                # if 'who' in event:
                #     e.contact = self._get_partial_contact(event['who'])
                # else:
                #     e.contact = self._get_partial_contact(event)

                # if not e.contact:
                #     continue

                # e.message = message % e.contact.name
                yield e

    # ---- CapMessages methods ---------------------

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        with self.browser:
            threads = self.browser.get_threads_list()

        for thread in threads:
            # Remove messages from user that quit
            #if thread['member'].get('isBan', thread['member'].get('dead', False)):
            #    with self.browser:
            #        self.browser.delete_thread(thread['member']['id'])
            #    continue
            t = Thread(int(thread['id']))
            t.flags = Thread.IS_DISCUSSION
            t.title = u'Discussion with %s' % thread['username']
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

        if not thread and isinstance(id, basestring) and not id.isdigit():
            for t in self.browser.get_threads_list():
                if t['username'] == id:
                    id = t['id']
                    break
            else:
                return None

        if not thread:
            thread = Thread(int(id))
            thread.flags = Thread.IS_DISCUSSION

        with self.browser:
            mails = self.browser.get_thread_mails(id)
            my_name = self.browser.get_my_name()

        child = None
        msg = None
        slut = self._get_slut(thread.id)
        if contacts is None:
            contacts = {}

        if not thread.title:
            thread.title = u'Discussion with %s' % mails['member']['pseudo']

        for mail in mails['messages']:
            flags = 0
            if mail['date'] > slut['lastmsg']:
                flags |= Message.IS_UNREAD

                if get_profiles:
                    if mail['id_from'] not in contacts:
                        with self.browser:
                            contacts[mail['id_from']] = self.get_contact(mail['id_from'])

            signature = u''
            if mail.get('src', None):
                signature += u'Sent from my %s\n\n' % mail['src']
            if contacts.get(mail['id_from'], None) is not None:
                signature += contacts[mail['id_from']].get_text()

            msg = Message(thread=thread,
                          id=int(time.strftime('%Y%m%d%H%M%S', mail['date'].timetuple())),
                          title=thread.title,
                          sender=mail['id_from'],
                          receivers=[my_name if mail['id_from'] != my_name else mails['member']['pseudo']],
                          date=mail['date'],
                          content=mail['message'],
                          signature=signature,
                          children=[],
                          flags=flags)
            if child:
                msg.children.append(child)
                child.parent = msg

            child = msg

        if msg:
            msg.parent = None

        thread.root = msg

        return thread

    def iter_unread_messages(self, thread=None):
        contacts = {}
        for thread in self.browser.get_threads_list():
            t = self.get_thread(thread['username'], contacts, get_profiles=True)
            for m in t.iter_all_messages():
                if m.flags & m.IS_UNREAD:
                    yield m

    def set_message_read(self, message):
        slut = self._get_slut(message.thread.id)
        if slut['lastmsg'] < message.date:
            slut['lastmsg'] = message.date
            self.storage.set('sluts', message.thread.id, slut)
            self.storage.save()

    def _get_slut(self, id):
        sluts = self.storage.get('sluts')
        if not sluts or id not in sluts:
            slut = {'lastmsg': datetime.datetime(1970,1,1)}
        else:
            slut = self.storage.get('sluts', id)

        slut['lastmsg'] = slut.get('lastmsg', datetime.datetime(1970,1,1)).replace(tzinfo=tz.tzutc())
        return slut

    # ---- CapMessagesPost methods ---------------------

    def post_message(self, message):
        content = message.content.replace('\n', '\r\n').encode('utf-8', 'replace')
        with self.browser:
            # Check wether we already have a thread with this user
            threads = self.browser.get_threads_list()
            for thread in threads:
                if thread['id'] == message.thread.id:
                    self.browser.post_reply(thread['id'], content)
                    break
            else:
                self.browser.post_mail(message.thread.id, content)

    # ---- CapContact methods ---------------------

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

            _id = profile['id']

            if isinstance(contact, Contact):
                contact.id = _id
                contact.name = profile['id']
            else:
                contact = Contact(_id, profile['id'], Contact.STATUS_OFFLINE)
            contact.url = 'http://%s/profile/%s' % (self.browser.DOMAIN, _id)
            contact.profile = profile['data']
            contact.summary = profile.get('summary', '')

            if contact.profile['details']['last_online'].value == u'Online now!':
                contact.status = Contact.STATUS_ONLINE
            else:
                contact.status = Contact.STATUS_OFFLINE
            contact.status_msg = contact.profile['details']['last_online'].value

            for no, photo in enumerate(self.browser.get_photos(_id)):
                contact.set_photo(u'image_%i' % no, url=photo, thumbnail_url=photo)
            return contact

    #def _get_partial_contact(self, contact):
    #    if contact.get('isBan', contact.get('dead', False)):
    #        with self.browser:
    #            self.browser.delete_thread(int(contact['id']))
    #        return None

    #    s = 0
    #    if contact.get('isOnline', False):
    #        s = Contact.STATUS_ONLINE
    #    else:
    #        s = Contact.STATUS_OFFLINE

    #    c = Contact(contact['id'], contact['id'], s)
    #    c.url = self.browser.id2url(contact['id'])
    #    if 'birthday' in contact:
    #        birthday = _parse_dt(contact['birthday'])
    #        age = int((datetime.datetime.now() - birthday).days / 365.25)
    #        c.status_msg = u'%s old, %s' % (age, contact['city'])
    #    if contact['cover'].isdigit() and int(contact['cover']) > 0:
    #        url = 'http://s%s.adopteunmec.com/%s%%(type)s%s.jpg' % (contact['shard'], contact['path'], contact['cover'])
    #    else:
    #        url = 'http://s.adopteunmec.com/www/img/thumb0.gif'

    #    c.set_photo('image%s' % contact['cover'],
    #                url=url % {'type': 'image'},
    #                thumbnail_url=url % {'type': 'thumb0_'})
    #    return c

    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        with self.browser:
            threads = self.browser.get_threads_list()

        for thread in threads:
            c = self.get_contact(thread['username'])
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
                return Query(id, 'A profile was visited')
            else:
                return Query(id, 'Unable to visit profile: it has been enqueued')
        else:
            with self.browser:
                if not self.browser.visit_profile(id):
                    raise QueryError('Could not visit profile')
                return Query(id, 'Profile was visited')

    #def get_notes(self, id):
    #    if isinstance(id, Contact):
    #        id = id.id

    #    return self.storage.get('notes', id)

    #def save_notes(self, id, notes):
    #    if isinstance(id, Contact):
    #        id = id.id

    #    self.storage.set('notes', id, notes)
    #    self.storage.save()

    OBJECTS = {Thread: fill_thread,
               Contact: fill_contact,
               ContactPhoto: fill_photo
              }

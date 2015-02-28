# -*- coding: utf-8 -*-

# Copyright(C) 2014      Roger Philibert
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


import datetime
from dateutil.parser import parse as parse_date
from dateutil.tz import tzlocal

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Thread, Message
from weboob.capabilities.dating import CapDating, Optimization
from weboob.capabilities.contact import CapContact, Contact, ProfileNode
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.date import local2utc
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.ordereddict import OrderedDict
from weboob.tools.log import getLogger

from .browser import HappnBrowser, FacebookBrowser


__all__ = ['HappnModule']


class ProfilesWalker(Optimization):
    def __init__(self, sched, storage, browser):
        super(ProfilesWalker, self).__init__()
        self._sched = sched
        self._storage = storage
        self._browser = browser
        self._logger = getLogger('walker', browser.logger)

        self._view_cron = None

    def start(self):
        self._view_cron = self._sched.schedule(1, self.view_profile)
        return True

    def stop(self):
        self._sched.cancel(self._view_cron)
        self._view_cron = None
        return True

    def set_config(self, params):
        pass

    def is_running(self):
        return self._view_cron is not None

    def view_profile(self):
        try:
            liked = self._storage.get('liked', default=[])

            n = 0
            for user in self._browser.find_users():
                if user['notifier']['id'] in liked:
                    continue

                self._browser.accept(user['notifier']['id'])
                liked.append(user['notifier']['id'])
                self._storage.set('liked', liked)
                self._storage.save()
                self._logger.info('Liked %s %s (%s at %s)', user['notifier']['first_name'], user['notifier']['last_name'], user['notifier']['job'], user['notifier']['workplace'])
                n += 1
                if n > 10:
                    break

        finally:
            if self._view_cron is not None:
                self._view_cron = self._sched.schedule(60, self.view_profile)


class HappnContact(Contact):
    def set_profile(self, *args):
        section = self.profile
        for arg in args[:-2]:
            try:
                s = section[arg]
            except KeyError:
                s = section[arg] = ProfileNode(arg, arg.capitalize().replace('_', ' '), OrderedDict(), flags=ProfileNode.SECTION)
            section = s.value

        key = args[-2]
        value = args[-1]
        section[key] = ProfileNode(key, key.capitalize().replace('_', ' '), value)

    def __init__(self, info):
        status = Contact.STATUS_OFFLINE
        last_seen = parse_date(info['modification_date'])
        if last_seen >= datetime.datetime.now(tzlocal()) - datetime.timedelta(minutes=30):
            status = Contact.STATUS_ONLINE

        super(HappnContact, self).__init__(info['id'], info['display_name'], status)

        self.summary = info['about']
        for photo in info['profiles']:
            self.set_photo(photo['id'], url=photo['url'])
        self.status_msg = u'Last seen at %s' % last_seen.strftime('%Y-%m-%d %H:%M:%S')
        self.url = NotAvailable

        self.profile = OrderedDict()

        self.set_profile('info', 'id', info['id'])
        self.set_profile('info', 'full_name', ' '.join([info['first_name'], info['last_name']]))
        self.set_profile('info', 'login', info['login'])
        if info['fb_id'] is not None:
            self.set_profile('info', 'facebook', 'https://www.facebook.com/profile.php?id=%s&fref=ufi&pnref=story' % info['fb_id'])
        if info['twitter_id'] is not None:
            self.set_profile('info', 'twitter', info['twitter_id'])
        self.set_profile('stats', 'accepted', info['is_accepted'])
        self.set_profile('stats', 'charmed', info['is_charmed'])
        self.set_profile('stats', 'unread_conversations', info['unread_conversations'])
        self.set_profile('stats', 'credits', info['credits'])
        if info['last_meet_position'] is not None:
            self.set_profile('geoloc', 'last_meet',
                             'https://www.google.com/maps/place//@%s,%s,17z' % (info['last_meet_position']['lat'],
                                                                                info['last_meet_position']['lon']))
        if info['distance'] is not None:
            self.set_profile('geoloc', 'distance', '%.2f km' % (info['distance']/1000.0))
        self.set_profile('details', 'gender', info['gender'])
        self.set_profile('details', 'age', '%s yo' % info['age'])
        self.set_profile('details', 'birthday', info['birth_date'])
        self.set_profile('details', 'job', info['job'])
        self.set_profile('details', 'company', info['workplace'])
        self.set_profile('details', 'school', info['school'])
        self.set_profile('settings', 'age_min', '%s yo' % info['matching_preferences']['age_min'])
        self.set_profile('settings', 'age_max', '%s yo' % info['matching_preferences']['age_max'])
        self.set_profile('settings', 'distance', '%s m' % info['matching_preferences']['distance'])
        self.set_profile('settings', 'female', info['matching_preferences']['female'])
        self.set_profile('settings', 'male', info['matching_preferences']['male'])


class HappnModule(Module, CapMessages, CapMessagesPost, CapDating, CapContact):
    NAME = 'happn'
    DESCRIPTION = u'Happn dating mobile application'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.1'
    CONFIG = BackendConfig(Value('username',                label='Facebook email'),
                           ValueBackendPassword('password', label='Facebook password'))

    BROWSER = HappnBrowser
    STORAGE = {'contacts': {},
               'liked': [],
              }

    def create_default_browser(self):
        facebook = FacebookBrowser()
        facebook.login(self.config['username'].get(),
                       self.config['password'].get())
        return HappnBrowser(facebook)

    # ---- CapDating methods -----------------------

    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))

    # ---- CapMessages methods ---------------------

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        for thread in self.browser.get_threads():
            t = Thread(thread['id'])
            t.flags = Thread.IS_DISCUSSION
            for user in thread['participants']:
                if user['user']['id'] != self.browser.my_id:
                    t.title = u'Discussion with %s' % user['user']['display_name']
            t.date = local2utc(parse_date(thread['modification_date']))
            yield t

    def get_thread(self, thread):
        if not isinstance(thread, Thread):
            thread = Thread(thread)
            thread.flags = Thread.IS_DISCUSSION

        info = self.browser.get_thread(thread.id)
        for user in info['participants']:
            if user['user']['id'] == self.browser.my_id:
                me = HappnContact(user['user'])
            else:
                other = HappnContact(user['user'])

        thread.title = u'Discussion with %s' % other.name

        contact = self.storage.get('contacts', thread.id, default={'lastmsg': 0})

        child = None

        for msg in info['messages']:
            flags = 0
            if int(contact['lastmsg']) < int(msg['id']):
                flags = Message.IS_UNREAD

            if msg['sender']['id'] == me.id:
                sender = me
                receiver = other
            else:
                sender = other
                receiver = me

            msg = Message(thread=thread,
                          id=msg['id'],
                          title=thread.title,
                          sender=sender.name,
                          receivers=[receiver.name],
                          date=local2utc(parse_date(msg['creation_date'])),
                          content=msg['message'],
                          children=[],
                          parent=None,
                          signature=sender.get_text(),
                          flags=flags)

            if child:
                msg.children.append(child)
                child.parent = msg
            child = msg
        thread.root = child

        return thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            thread = self.get_thread(thread)
            for message in thread.iter_all_messages():
                if message.flags & message.IS_UNREAD:
                    yield message

    def set_message_read(self, message):
        contact = self.storage.get('contacts', message.thread.id, default={'lastmsg': 0})
        if int(contact['lastmsg']) < int(message.id):
            contact['lastmsg'] = int(message.id)
            self.storage.set('contacts', message.thread.id, contact)
            self.storage.save()

    # ---- CapMessagesPost methods ---------------------

    def post_message(self, message):
        self.browser.post_message(message.thread.id, message.content)

    # ---- CapContact methods ---------------------
    def get_contact(self, contact_id):
        if isinstance(contact_id, Contact):
            contact_id = contact_id.id

        info = self.browser.get_contact(contact_id)
        return HappnContact(info)

    OBJECTS = {Thread: fill_thread,
              }

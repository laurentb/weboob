# -*- coding: utf-8 -*-

# Copyright(C) 2014      Roger Philibert
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

from collections import OrderedDict
import datetime
from random import randint, random

from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from dateutil.tz import tzlocal
import geopy
import geopy.distance

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Thread, Message
from weboob.capabilities.dating import CapDating, Optimization
from weboob.capabilities.contact import CapContact, Contact, ProfileNode
from weboob.exceptions import BrowserHTTPError
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.log import getLogger

from .browser import HappnBrowser, FacebookBrowser


__all__ = ['HappnModule']


class ProfilesWalker(Optimization):
    def __init__(self, sched, storage, browser, location, distance):
        super(ProfilesWalker, self).__init__()
        self._sched = sched
        self._storage = storage
        self._browser = browser
        self._logger = getLogger('walker', browser.logger)
        self._last_position_update = None

        self._view_cron = None

        self._location = geopy.Point(map(float, location.split(',')))
        self._max_distance = int(distance)

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
            n = 0
            for user in self._browser.find_users():
                if user['notifier']['my_relation'] > 0:
                    continue

                self._browser.accept(user['notifier']['id'])
                fb = self._browser.get_facebook(user['notifier']['fb_id'])
                self._logger.info('Liked %s (%s at %s): %s',
                                  fb['name'],
                                  user['notifier']['job'],
                                  user['notifier']['workplace'],
                                  fb['link'])
                n += 1
                if n > 10:
                    break

            if n == 0 and (self._last_position_update is None or self._last_position_update + datetime.timedelta(minutes=20) < datetime.datetime.now()):
                self._logger.info('No more new profiles, updating position...')

                d = geopy.distance.VincentyDistance(kilometers=random()*self._max_distance)
                pos = d.destination(point=self._location, bearing=randint(0,360))
                try:
                    pos = self._browser.set_position(pos.latitude, pos.longitude)
                except BrowserHTTPError:
                    self._logger.warning('Unable to update position for now, it will be retried later.')
                    self._logger.warning('NB: don\'t be afraid, happn only allows to update position every 20 minutes.')
                else:
                    self._logger.info('You are now here: https://www.google.com/maps/place//@%s,%s,17z', pos['latitude'], pos['longitude'])
                    self._last_position_update = datetime.datetime.now()

            for thread in self._browser.get_threads():
                other_name = ''
                for user in thread['participants']:
                    if user['user']['id'] != self._browser.my_id:
                        other_name = user['user']['display_name']

                if len(thread['messages']) == 0 and parse_date(thread['creation_date']) < (datetime.datetime.now(tzlocal()) - relativedelta(hours=1)):
                    self._browser.post_message(thread['id'], u'Coucou %s :)' % other_name)
                    self._logger.info(u'Welcome message sent to %s' % other_name)
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
        try:
            self.set_profile('info', 'full_name', info['fb']['name'])
        except KeyError:
            self.set_profile('info', 'full_name', ' '.join([info['first_name'] or '', info['last_name'] or '']).strip())
        if 'fb' in info:
            self.set_profile('info', 'facebook', info['fb']['link'])
            self.set_profile('facebook', 'likes', 'interests', ', '.join(info['fb']['likes']))
            for name, content in info['fb']['infos'].iteritems():
                self.set_profile('facebook', 'infos', name, content)
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
        if info['matching_preferences'] is not None:
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
    VERSION = '1.6'
    CONFIG = BackendConfig(Value('username',                label='Facebook email'),
                           ValueBackendPassword('password', label='Facebook password'),
                           Value('location',                label='Location (example: 49.6008457,6.129709)'),
                           Value('distance',                label='Distance (in km) around your location you\'re walking'))

    BROWSER = HappnBrowser
    STORAGE = {'contacts': {},
              }

    def create_default_browser(self):
        facebook = self.create_browser(klass=FacebookBrowser)
        facebook.login(self.config['username'].get(),
                       self.config['password'].get())
        return self.create_browser(facebook)

    # ---- CapDating methods -----------------------

    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser,
                                                               self.config['location'].get(),
                                                               self.config['distance'].get()))

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
            t.date = parse_date(thread['modification_date'])
            yield t

    def get_thread(self, thread):
        if not isinstance(thread, Thread):
            thread = Thread(thread)
            thread.flags = Thread.IS_DISCUSSION

        info = self.browser.get_thread(thread.id)
        for user in info['participants']:
            if user['user']['fb_id'] is not None:
                user['user']['fb'] = self.browser.get_facebook(user['user']['fb_id'])
            if user['user']['id'] == self.browser.my_id:
                me = HappnContact(user['user'])
            else:
                other = HappnContact(user['user'])

        thread.title = u'Discussion with %s' % other.name

        contact = self.storage.get('contacts', thread.id, default={'lastmsg_date': '1970-01-01T01:01:01+00:00'})

        child = None

        for msg in info['messages']:
            flags = 0
            if parse_date(contact['lastmsg_date']) < parse_date(msg['creation_date']):
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
                          date=parse_date(msg['creation_date']),
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
        contact = self.storage.get('contacts', message.thread.id, default={'lastmsg_date': '1970-01-01T01:01:01+00:00'})
        if parse_date(contact['lastmsg_date']) < message.date:
            contact['lastmsg_date'] = str(message.date)
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

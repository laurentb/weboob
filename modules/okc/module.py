# -*- coding: utf-8 -*-

# Copyright(C) 2012-2016 Roger Philibert
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

from collections import OrderedDict
from datetime import datetime
from html2text import unescape

from weboob.capabilities.contact import CapContact, ContactPhoto, Contact, ProfileNode
from weboob.capabilities.dating import CapDating
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message, Thread
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.misc import to_unicode
from weboob.tools.value import Value, ValueBackendPassword

from .browser import OkCBrowser
from .optim.profiles_walker import ProfilesWalker


__all__ = ['OkCModule']

class OkcContact(Contact):
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

    def __init__(self, profile):
        super(OkcContact, self).__init__(profile['userid'],
                                         profile['username'],
                                         self.STATUS_ONLINE if profile['is_online'] == '1' else self.STATUS_OFFLINE)

        self.url = 'https://www.okcupid.com/profile/%s' % self.name
        self.summary = profile.get('summary', '')
        self.status_msg = 'Last connection at %s' % profile['skinny']['last_online']

        for no, photo in enumerate(profile['photos']):
            self.set_photo(u'image_%i' % no, url=photo['image_url'], thumbnail_url=photo['image_url'])

        self.profile = OrderedDict()

        self.set_profile('info', 'status', profile['status_str'])
        self.set_profile('info', 'orientation', profile['orientation_str'])
        self.set_profile('info', 'age', '%s yo' % profile['age'])
        self.set_profile('info', 'birthday', '%04d-%02d-%02d' % (profile['birthday']['year'], profile['birthday']['month'], profile['birthday']['day']))
        self.set_profile('info', 'sex', profile['gender_str'])
        self.set_profile('info', 'location', profile['location'])
        self.set_profile('info', 'join_date', profile['skinny']['join_date'])
        self.set_profile('stats', 'match_percent', '%s%%' % profile['matchpercentage'])
        self.set_profile('stats', 'friend_percent', '%s%%' % profile['friendpercentage'])
        self.set_profile('stats', 'enemy_percent', '%s%%' % profile['enemypercentage'])
        for key, value in sorted(profile['skinny'].items()):
            self.set_profile('details', key, value or '-')

        for essay in profile['essays']:
            if len(essay['essay']) == 0:
                continue

            self.summary += '%s:\n' % essay['title']
            self.summary += '-' * (len(essay['title']) + 1)
            self.summary += '\n'
            for text in essay['essay']:
                self.summary += text['rawtext']
            self.summary += '\n\n'

        self.profile['info'].flags |= ProfileNode.HEAD
        self.profile['stats'].flags |= ProfileNode.HEAD



class OkCModule(Module, CapMessages, CapContact, CapMessagesPost, CapDating):
    NAME = 'okc'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '1.4'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'OkCupid'
    CONFIG = BackendConfig(Value('username',                label='Username'),
                           ValueBackendPassword('password', label='Password'))
    STORAGE = {'profiles_walker': {'viewed': []},
               'sluts': {},
              }
    BROWSER = OkCBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['username'].get(), self.config['password'].get())

    # ---- CapDating methods ---------------------
    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))

    # ---- CapMessages methods ---------------------
    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        threads = self.browser.get_threads_list()

        for thread in threads:
            t = Thread(thread['userid'])
            t.flags = Thread.IS_DISCUSSION
            t.title = u'Discussion with %s' % thread['user']['username']
            t.date = datetime.fromtimestamp(thread['timestamp'])
            yield t

    def get_thread(self, thread):
        if not isinstance(thread, Thread):
            thread = Thread(thread)
            thread.flags = Thread.IS_DISCUSSION

        messages = self.browser.get_thread_messages(thread.id)

        contact = self.storage.get('sluts', thread.id, default={'lastmsg': datetime(1970,1,1)})
        thread.title = u'Discussion with %s' % messages['fields']['username']

        me = OkcContact(self.browser.get_profile(self.browser.me['userid']))
        other = OkcContact(self.browser.get_profile(thread.id))

        parent = None
        for message in messages['messages']['messages']:
            date = datetime.fromtimestamp(message['timestamp'])

            flags = 0
            if contact['lastmsg'] < date:
                flags = Message.IS_UNREAD

            if message['from'] == thread.id:
                sender = other
                receiver = me
            else:
                receiver = other
                sender = me

            msg = Message(thread=thread,
                          id=message['id'],
                          title=thread.title,
                          sender=sender.name,
                          receivers=[receiver.name],
                          date=date,
                          content=to_unicode(unescape(message['body'])),
                          children=[],
                          parent=parent,
                          signature=sender.get_text(),
                          flags=flags)

            if parent:
                parent.children = [msg]
            else:
                thread.root = msg

            parent = msg

        return thread

    def iter_unread_messages(self):
        for thread in self.iter_threads():
            contact = self.storage.get('sluts', thread.id, default={'lastmsg': datetime(1970,1,1)})
            if thread.date <= contact['lastmsg']:
                continue

            thread = self.get_thread(thread)
            for message in thread.iter_all_messages():
                if message.flags & message.IS_UNREAD:
                    yield message

    def set_message_read(self, message):
        contact = self.storage.get('sluts', message.thread.id, default={'lastmsg': datetime(1970,1,1)})
        if contact['lastmsg'] < message.date:
            contact['lastmsg'] = message.date
            self.storage.set('sluts', message.thread.id, contact)
            self.storage.save()

    # ---- CapMessagesPost methods ---------------------
    def post_message(self, message):
        self.browser.post_message(message.thread.id, message.content)

    # ---- CapContact methods ---------------------
    def fill_contact(self, contact, fields):
        if 'profile' in fields:
            contact = self.get_contact(contact)
        if contact and 'photos' in fields:
            for name, photo in contact.photos.iteritems():
                if photo.url and not photo.data:
                    data = self.browser.open(photo.url).content
                    contact.set_photo(name, data=data)
                if photo.thumbnail_url and not photo.thumbnail_data:
                    data = self.browser.open(photo.thumbnail_url).content
                    contact.set_photo(name, thumbnail_data=data)

    def fill_photo(self, photo, fields):
        if 'data' in fields and photo.url and not photo.data:
            photo.data = self.browser.open(photo.url).content
        if 'thumbnail_data' in fields and photo.thumbnail_url and not photo.thumbnail_data:
            photo.thumbnail_data = self.browser.open(photo.thumbnail_url).content
        return photo

    def get_contact(self, user_id):
        if isinstance(user_id, Contact):
            user_id = user_id.id

        info = self.browser.get_profile(user_id)

        return OkcContact(info)

    def iter_contacts(self, status=Contact.STATUS_ALL, ids=None):
        threads = self.browser.get_threads_list()

        for thread in threads:
            c = self.get_contact(thread['user']['username'])
            if c and (c.status & status) and (not ids or c.id in ids):
                yield c

    OBJECTS = {Thread: fill_thread,
               Contact: fill_contact,
               ContactPhoto: fill_photo
              }

# -*- coding: utf-8 -*-

# Copyright(C) 2012-2016 Roger Philibert
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
from datetime import datetime

try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser

from weboob.capabilities.contact import CapContact, ContactPhoto, Contact, ProfileNode
from weboob.capabilities.dating import CapDating
from weboob.capabilities.messages import CapMessages, CapMessagesPost, Message, Thread
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.misc import to_unicode
from weboob.tools.value import Value, ValueBackendPassword, ValueBool

from .browser import OkCBrowser, FacebookBrowser
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
        super(OkcContact, self).__init__(profile['user']['userid'],
                                         profile['user']['userinfo']['displayname'],
                                         self.STATUS_ONLINE if profile['user']['online'] else self.STATUS_OFFLINE)

        self.url = 'https://www.okcupid.com/profile/%s' % self.id
        self.summary = u''
        self.status_msg = profile['extras']['lastOnlineString']

        for no, photo in enumerate(profile['user']['photos']):
            self.set_photo(u'image_%i' % no, url=photo['full'], thumbnail_url=photo['full_small'])

        self.profile = OrderedDict()

        if isinstance(profile['user']['details'], dict):
            for key, label in profile['user']['details']['_labels'].items():
                self.set_profile('info', label, profile['user']['details']['values'][key])
        else:
            for section in profile['user']['details']:
                self.set_profile('info', section['info']['name'], section['text']['text'])

        self.set_profile('info', 'orientation', profile['user']['userinfo']['orientation'])
        self.set_profile('info', 'age', '%s yo' % profile['user']['userinfo']['age'])
        self.set_profile('info', 'sex', profile['user']['userinfo']['gender'])
        self.set_profile('info', 'location', profile['user']['userinfo']['location'])
        self.set_profile('stats', 'match_percent', '%s%%' % profile['user']['percentages']['match'])
        self.set_profile('stats', 'enemy_percent', '%s%%' % profile['user']['percentages']['enemy'])
        if 'friend' in profile['user']['percentages']:
            self.set_profile('stats', 'friend_percent', '%s%%' % profile['user']['percentages']['friend'])

        for essay in profile['user']['essays']:
            if not essay['content']:
                continue

            self.summary += '%s:\n' % essay['title']
            self.summary += '-' * (len(essay['title']) + 1)
            self.summary += '\n'
            self.summary += essay['rawtext']
            self.summary += '\n\n'

        self.profile['info'].flags |= ProfileNode.HEAD
        self.profile['stats'].flags |= ProfileNode.HEAD



class OkCModule(Module, CapMessages, CapContact, CapMessagesPost, CapDating):
    NAME = 'okc'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    VERSION = '2.1'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = u'OkCupid'
    CONFIG = BackendConfig(Value('username',                label='Username'),
                           ValueBackendPassword('password', label='Password'),
                           ValueBool('facebook', label='Do you login with Facebook?', default=False))
    STORAGE = {'profiles_walker': {'viewed': []},
               'sluts': {},
              }
    BROWSER = OkCBrowser

    def create_default_browser(self):
        if int(self.config['facebook'].get()):
            facebook = self.create_browser(klass=FacebookBrowser)
            facebook.login(self.config['username'].get(), self.config['password'].get())
        else:
            facebook = None
        return self.create_browser(self.config['username'].get(),
                                   self.config['password'].get(),
                                   facebook)

    # ---- CapDating methods ---------------------
    def init_optimizations(self):
        self.add_optimization('PROFILE_WALKER', ProfilesWalker(self.weboob.scheduler, self.storage, self.browser))

    # ---- CapMessages methods ---------------------
    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        threads = self.browser.get_threads_list()

        for thread in threads:
            t = Thread(thread['user']['userid'])
            t.flags = Thread.IS_DISCUSSION
            t.title = u'Discussion with %s' % thread['user']['userinfo']['displayname']
            t.date = datetime.fromtimestamp(thread['time'])
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
        for message in messages['messages']:
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
                if message.get('read', False):
                    flags |= Message.IS_RECEIVED
                    # Apply that flag on all previous messages as the 'read'
                    # attribute is only set on the last read message.
                    pmsg = parent
                    while pmsg:
                        if pmsg.flags & Message.IS_NOT_RECEIVED:
                            pmsg.flags |= Message.IS_RECEIVED
                            pmsg.flags &= ~Message.IS_NOT_RECEIVED
                        pmsg = pmsg.parent
                else:
                    flags |= Message.IS_NOT_RECEIVED


            msg = Message(thread=thread,
                          id=message['id'],
                          title=thread.title,
                          sender=sender.name,
                          receivers=[receiver.name],
                          date=date,
                          content=to_unicode(HTMLParser().unescape(message['body'])),
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
            for name, photo in contact.photos.items():
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

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

from weboob.capabilities.messages import CapMessages, CapMessagesPost, Thread, Message
from weboob.capabilities.dating import CapDating
from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.date import local2utc

from .browser import PlayMeBrowser, FacebookBrowser


__all__ = ['PlayMeModule']


class PlayMeModule(Module, CapMessages, CapMessagesPost, CapDating):
    NAME = 'playme'
    DESCRIPTION = u'PlayMe dating mobile application'
    MAINTAINER = u'Roger Philibert'
    EMAIL = 'roger.philibert@gmail.com'
    LICENSE = 'AGPLv3+'
    VERSION = '1.0'
    CONFIG = BackendConfig(Value('username',                label='Facebook email'),
                           ValueBackendPassword('password', label='Facebook password'))

    BROWSER = PlayMeBrowser
    STORAGE = {'contacts': {},
              }

    def create_default_browser(self):
        facebook = FacebookBrowser()
        facebook.login(self.config['username'].get(),
                       self.config['password'].get())
        return PlayMeBrowser(facebook)

    # ---- CapMessages methods ---------------------

    def fill_thread(self, thread, fields):
        return self.get_thread(thread)

    def iter_threads(self):
        for thread in self.browser.get_threads():
            t = Thread(thread['id'])
            t.flags = Thread.IS_DISCUSSION
            t.title = u'Discussion with %s' % thread['name']
            t.date = local2utc(datetime.datetime.fromtimestamp(thread['last_message']['utc_timestamp']))
            yield t

    def get_thread(self, thread):
        if not isinstance(thread, Thread):
            thread = Thread(thread)
            thread.flags = Thread.IS_DISCUSSION

        user = self.browser.get_user(thread.id)
        thread.title = u'Discussion with %s' % user['name']

        contact = self.storage.get('contacts', thread.id, default={'lastmsg': 0})

        signature = u'Age: %s' % user['age']
        signature += u'\nLast online: %s' % user['last_online']
        signature += u'\nPhotos:\n\t%s' % '\n\t'.join([user['photo_host'] + photo['large'] for photo in user['photos']])

        child = None

        for msg in self.browser.get_thread_messages(thread.id):
            flags = 0
            if int(contact['lastmsg']) < msg['utc_timestamp']:
                flags = Message.IS_UNREAD

            if msg['type'] == 'msg':
                content = unicode(msg['msg'])
            elif msg['type'] == 'new_challenge':
                content = u'A new challenge has been proposed!'
            elif msg['type'] == 'serie':
                content = u"I've played"
            elif msg['type'] == 'end_game':
                content = u'%s is the winner! (%s VS %s)' % (self.browser.my_name if msg['score']['w'] == self.browser.my_id else user['name'], msg['score']['s'][0], msg['score']['s'][1])
            else:
                content = u'Unknown action: %s' % msg['type']

            msg = Message(thread=thread,
                          id=msg['utc_timestamp'],
                          title=thread.title,
                          sender=unicode(self.browser.my_name if msg['from'] == self.browser.my_id else user['name']),
                          receivers=[unicode(self.browser.my_name if msg['from'] != self.browser.my_id else user['name'])],
                          date=local2utc(datetime.datetime.fromtimestamp(msg['utc_timestamp'])),
                          content=content,
                          children=[],
                          parent=None,
                          signature=signature if msg['from'] != self.browser.my_id else u'',
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

    OBJECTS = {Thread: fill_thread,
              }

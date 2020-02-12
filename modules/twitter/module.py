# -*- coding: utf-8 -*-

# Copyright(C) 2014      Bezleputh
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

from datetime import datetime, timedelta
from weboob.tools.value import Value, ValueBackendPassword
from weboob.tools.backend import Module, BackendConfig
from weboob.capabilities.messages import CapMessages, Thread, CapMessagesPost
from weboob.capabilities.collection import CapCollection, CollectionNotFound, Collection
from weboob.capabilities.base import find_object
from weboob.exceptions import BrowserForbidden
from .browser import TwitterBrowser
import itertools

__all__ = ['TwitterModule']


class TwitterModule(Module, CapMessages, CapMessagesPost, CapCollection):
    NAME = 'twitter'
    DESCRIPTION = u'twitter website'
    MAINTAINER = u'Bezleputh'
    EMAIL = 'carton_ben@yahoo.fr'
    LICENSE = 'AGPLv3+'
    VERSION = '2.1'
    BROWSER = TwitterBrowser
    STORAGE = {'seen': {}}

    CONFIG = BackendConfig(Value('username',                label='Username', default=''),
                           ValueBackendPassword('password', label='Password', default=''),
                           Value('hashtags_subscribe',      label='Hashtags subscribe', default=''),
                           Value('search_subscribe',        label='Search subscribe', default=''),
                           Value('profils_subscribe',       label='Profils subscribe', default=''))

    def create_default_browser(self):
        username = self.config['username'].get()
        if username:
            password = self.config['password'].get()
        else:
            password = None

        return self.create_browser(username, password)

    def iter_threads(self):
        if self.config['username'].get():
            return self.browser.iter_threads()
        else:
            profils = self.config['profils_subscribe'].get()
            hashtags = self.config['hashtags_subscribe'].get()
            searchs = self.config['search_subscribe'].get()
            tweets = []
            if profils:
                for profil in profils.split(','):
                    for tweet in itertools.islice(self.browser.get_tweets_from_profil(profil), 0, 20):
                        tweets.append(tweet)

            if hashtags:
                for hashtag in hashtags.split(','):
                    for tweet in itertools.islice(self.browser.get_tweets_from_hashtag(hashtag), 0, 20):
                        tweets.append(tweet)

            if searchs:
                for search in searchs.split(','):
                    for tweet in itertools.islice(self.browser.get_tweets_from_search(search), 0, 20):
                        tweets.append(tweet)

            tweets.sort(key=lambda o: o.date, reverse=True)
            return tweets

    def get_thread(self, _id, thread=None, getseen=True):
        seen = None
        if getseen:
            seen = self.storage.get('seen', default={})
        return self.browser.get_thread(_id, thread, seen)

    def fill_thread(self, thread, fields, getseen=True):
        return self.get_thread(thread.id, thread, getseen)

    def set_message_read(self, message):
        self.storage.set('seen', message.thread.id, message.thread.date)
        self.storage.save()
        self._purge_message_read()

    def _purge_message_read(self):
        lastpurge = self.storage.get('lastpurge', default=datetime.now() - timedelta(days=60))

        if datetime.now() - lastpurge > timedelta(days=60):
            self.storage.set('lastpurge', datetime.now() - timedelta(days=60))
            self.storage.save()

            # we can't directly delete without a "RuntimeError: dictionary changed size during iteration"
            todelete = []

            for id, date in self.storage.get('seen', default={}).items():
                # if no date available, create a new one (compatibility with "old" storage)
                if not date:
                    self.storage.set('seen', id, datetime.now())
                elif lastpurge > date:
                    todelete.append(id)

            for id in todelete:
                self.storage.delete('seen', id)
            self.storage.save()

    def post_message(self, message):
        if not self.config['username'].get():
            raise BrowserForbidden()
        self.browser.post(find_object(self.iter_threads(), id=message.full_id.split('.')[0]),
                          message.content)

    def iter_resources(self, objs, split_path):
        collection = self.get_collection(objs, split_path)
        if collection.path_level == 0:
            if self.config['username'].get():
                yield Collection([u'me'], u'me')
            yield Collection([u'profils'], u'profils')
            yield Collection([u'trendy'], u'trendy')
            yield Collection([u'hashtags'], u'hashtags')
            yield Collection([u'search'], u'search')

        if collection.path_level == 1:
            if collection.split_path[0] == u'me':
                for el in self.browser.get_tweets_from_profil(self.browser.get_me()):
                    yield el

            if collection.split_path[0] == u'profils':
                profils = self.config['profils_subscribe'].get()
                if profils:
                    for profil in profils.split(','):
                        yield Collection([profil], profil)

            if collection.split_path[0] == u'hashtags':
                hashtags = self.config['hashtags_subscribe'].get()
                if hashtags:
                    for hashtag in hashtags.split(','):
                        yield Collection([hashtag], hashtag)

            if collection.split_path[0] == u'search':
                searchs = self.config['search_subscribe'].get()
                if searchs:
                    for search in searchs.split(','):
                        yield Collection([search], search)

            if collection.split_path[0] == u'trendy':
                for obj in self.browser.get_trendy_subjects():
                    yield Collection([obj.id], obj.id)

        if collection.path_level == 2:
            if collection.split_path[0] == u'profils':
                for el in self.browser.get_tweets_from_profil(collection.split_path[1]):
                    yield el

            if collection.split_path[0] == u'trendy':
                if collection.split_path[1].startswith('#'):
                    for el in self.browser.get_tweets_from_hashtag(collection.split_path[1]):
                        yield el
                else:
                    for el in self.browser.get_tweets_from_search(collection.split_path[1]):
                        yield el

            if collection.split_path[0] == u'hashtags':
                for el in self.browser.get_tweets_from_hashtag(collection.split_path[1]):
                    yield el

            if collection.split_path[0] == u'search':
                for el in self.browser.get_tweets_from_search(collection.split_path[1]):
                    yield el

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if collection.path_level == 1 and collection.split_path[0] in \
           [u'profils', u'trendy', u'me', u'hashtags', u'search']:
            return
        if collection.path_level == 2:
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {Thread: fill_thread}

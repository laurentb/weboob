# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value
from weboob.capabilities.image import CapImage, BaseImage, Thumbnail
from weboob.capabilities.messages import CapMessages, Thread
from weboob.capabilities.collection import CapCollection, Collection

from .browser import RedditBrowser


__all__ = ['RedditModule']


def register_resources_handler(d, *path):
    def decorator(func):
        d[path] = func
        return func
    return decorator


class RedditModule(Module, CapImage, CapCollection, CapMessages):
    NAME = 'reddit'
    DESCRIPTION = u'reddit website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.5'
    CONFIG = BackendConfig(
        Value('subreddit', label='Name of the sub-reddit', regexp='[^/]+', default='pics'),
    )

    BROWSER = RedditBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['subreddit'].get())

    def get_file(self, _id):
        raise NotImplementedError()

    def get_image(self, id):
        return self.browser.get_image(id)

    def search_file(self, pattern, sortby=CapImage.SEARCH_RELEVANCE):
        return self.browser.search_images(pattern, sortby, True)

    def search_image(self, pattern, sortby=CapImage.SEARCH_RELEVANCE, nsfw=False):
        sorting = {
            CapImage.SEARCH_RELEVANCE: 'relevance',
            CapImage.SEARCH_RATING: 'top',
            CapImage.SEARCH_VIEWS: 'top', # not implemented
            CapImage.SEARCH_DATE: 'new',
        }
        sortby = sorting[sortby]
        return self.browser.search_images(pattern, sortby, nsfw)

    def iter_threads(self):
        return self.browser.iter_threads()

    def get_thread(self, id):
        return self.browser.get_thread(id)

    def iter_resources(self, objs, split_path):
        for k in self.RESOURCES:
            if len(k) == len(split_path) and all(a is None or a == b for a, b in zip(k, split_path)):
                f = self.RESOURCES[k]
                return f(self, objs, *split_path)

    RESOURCES = {}

    @register_resources_handler(RESOURCES)
    def iter_resources_root(self, objs):
        return [
            Collection(['hot'], 'Hot threads'),
            Collection(['new'], 'New threads'),
            Collection(['rising'], 'Rising threads'),
            Collection(['controversial'], 'Controversial threads'),
            Collection(['top'], 'Top threads'),
        ]

    @register_resources_handler(RESOURCES, None)
    def iter_resources_dir(self, objs, key):
        if key == 'hot':
            key = ''

        if Thread in objs:
            return self.iter_threads(cat=key)
        if BaseImage in objs:
            return self.browser.iter_images(cat=key)
        return []

    def fill_data(self, obj, fields):
        if 'thumbnail' in fields and not obj.thumbnail.data:
            obj.thumbnail.data = self.browser.open(obj.thumbnail.url).content
        if 'data' in fields:
            obj.data = self.browser.open(obj.url).content

    def fill_thread(self, obj, fields):
        if 'root' in fields:
            self.browser.fill_thread(obj)

    OBJECTS = {
        BaseImage: fill_data,
        Thumbnail: fill_data,
        Thread: fill_thread,
    }

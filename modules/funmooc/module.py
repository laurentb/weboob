# -*- coding: utf-8 -*-

# Copyright(C) 2015      Vincent A
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


from weboob.tools.backend import Module, BackendConfig
from weboob.tools.value import Value, ValueBackendPassword
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.capabilities.video import CapVideo, BaseVideo

from .browser import FunmoocBrowser

__all__ = ['FunmoocModule']


class FunmoocModule(Module, CapVideo, CapCollection):
    NAME = 'funmooc'
    DESCRIPTION = u'France-Université-Numérique MOOC website'
    MAINTAINER = u'Vincent A'
    EMAIL = 'dev@indigo.re'
    LICENSE = 'AGPLv3+'
    VERSION = '1.4'

    CONFIG = BackendConfig(Value('email', label='Email'),
                           ValueBackendPassword('password', label='Password'),
                           Value('quality', label='Quality', default='HD',
                                 choices=['HD', 'SD', 'LD']))

    BROWSER = FunmoocBrowser

    def create_default_browser(self):
        quality = self.config['quality'].get().upper()
        return self.create_browser(self.config['email'].get(),
                                   self.config['password'].get(),
                                   quality=quality)

    def get_video(self, _id):
        return self.browser.get_video(_id)

    def iter_resources(self, objs, split_path):
        if len(split_path) == 0:
            return self.browser.iter_courses()
        elif len(split_path) == 1:
            return self.browser.iter_chapters(*split_path)
        elif len(split_path) == 2:
            return self.browser.iter_sections(*split_path)
        elif len(split_path) == 3:
            return self.browser.iter_videos(*split_path)

    def _matches(self, title, pattern):
        title = title.lower()
        words = pattern.lower().split()
        return all(word in title for word in words)

    def search_videos(self, pattern, sortby=0, nsfw=False):
        queue = [[]]
        while len(queue):
            path = queue.pop()
            for item in self.iter_resources(BaseVideo, path):
                if isinstance(item, BaseVideo):
                    if self._matches(item.title, pattern):
                        yield item
                else: # collection
                    newpath = item.split_path
                    if self._matches(item.title, pattern):
                        self.logger.debug('%s matches, returning content',
                                          item.title)
                        for item in self.iter_resources_flat(BaseVideo, newpath):
                            yield item
                        return
                    queue.append(newpath)

    def validate_collection(self, objs, collection):
        if not self.browser.check_collection(collection.split_path):
            raise CollectionNotFound()

# -*- coding: utf-8 -*-

# Copyright(C) 2011  Clément Schreiner
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
from weboob.capabilities.content import CapContent, Content
from weboob.capabilities.file import CapFile
from weboob.capabilities.image import CapImage, BaseImage, Thumbnail
from weboob.tools.value import ValueBackendPassword, Value


from .browser import MediawikiBrowser


__all__ = ['MediawikiModule']


class WikiImage(BaseImage):
    @property
    def page_url(self):
        return self._canonical_url


class MediawikiModule(Module, CapContent, CapImage):
    NAME = 'mediawiki'
    MAINTAINER = u'Clément Schreiner'
    EMAIL = 'clemux@clemux.info'
    VERSION = '1.2'
    LICENSE = 'AGPLv3+'
    DESCRIPTION = 'Wikis running MediaWiki, like Wikipedia'
    CONFIG = BackendConfig(Value('url',      label='URL of the Mediawiki website', default='http://en.wikipedia.org/', regexp='https?://.*'),
                           Value('apiurl',   label='URL of the Mediawiki website\'s API', default='http://en.wikipedia.org/w/api.php', regexp='https?://.*'),
                           Value('username', label='Login', default=''),
                           ValueBackendPassword('password', label='Password', default=''))

    BROWSER = MediawikiBrowser

    def create_default_browser(self):
        username = self.config['username'].get()
        if len(username) > 0:
            password = self.config['password'].get()
        else:
            password = ''
        return self.create_browser(self.config['url'].get(),
                                   self.config['apiurl'].get(),
                                   username, password)

    def get_content(self, _id, revision=None):
        _id = _id.replace(' ', '_')
        content = Content(_id)
        page = _id
        rev = revision.id if revision else None
        data = self.browser.get_wiki_source(page, rev)

        content.content = data
        return content

    def iter_revisions(self, _id):
        return self.browser.iter_wiki_revisions(_id)

    def push_content(self, content, message=None, minor=False):
        self.browser.set_wiki_source(content, message, minor)

    def get_content_preview(self, content):
        return self.browser.get_wiki_preview(content)

    def _make_image(self, info):
        img = WikiImage(info['title'])
        if 'thumbnail' in info:
            thumb = Thumbnail(info['thumbnail'])
            img.thumbnail = thumb
        if 'original' in info:
            img.url = info['original']
        img._canonical_url = info['canonicalurl']
        img.size = info['size']

        return img

    def search_file(self, pattern, sortby=CapFile.SEARCH_RELEVANCE):
        for info in self.browser.search_file(pattern):
            yield self._make_image(info)

    def get_image(self, _id):
        _id = _id.replace(' ', '_')
        info = self.browser.get_image(_id)
        return self._make_image(info)

    def fill_img(self, obj, fields):
        if set(fields) & set(('url', 'thumbnail')):
            new = self.get_image(obj.id)
            if not obj.url:
                obj.url = new.url
            if not obj.thumbnail:
                obj.thumbnail = new.thumbnail
        if 'data' in fields:
            obj.data = self.browser.open(obj.url).content
        return obj

    OBJECTS = {BaseImage: fill_img, Thumbnail: fill_img}

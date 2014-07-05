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



from weboob.tools.backend import BaseBackend, BackendConfig
from weboob.capabilities.content import CapContent, Content
from weboob.tools.value import ValueBackendPassword, Value


from .browser import MediawikiBrowser


__all__ = ['MediawikiBackend']


class MediawikiBackend(BaseBackend, CapContent):
    NAME = 'mediawiki'
    MAINTAINER = u'Clément Schreiner'
    EMAIL = 'clemux@clemux.info'
    VERSION = '0.j'
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
            password = None
        return self.create_browser(self.config['url'].get(),
                                   self.config['apiurl'].get(),
                                   username, password)

    def get_content(self, _id, revision=None):
        _id = _id.replace(' ', '_')
        content = Content(_id)
        page = _id
        rev = revision.id if revision else None
        with self.browser:
            data = self.browser.get_wiki_source(page, rev)

        content.content = data
        return content

    def iter_revisions(self, _id):
        return self.browser.iter_wiki_revisions(_id)

    def push_content(self, content, message=None, minor=False):
        self.browser.set_wiki_source(content, message, minor)

    def get_content_preview(self, content):
        return self.browser.get_wiki_preview(content)

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
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


from __future__ import with_statement

from weboob.capabilities.content import ICapContent, Content
from weboob.tools.backend import BaseBackend
from weboob.tools.value import ValuesDict, Value

from .browser import RedmineBrowser


__all__ = ['RedmineBackend']


class RedmineBackend(BaseBackend, ICapContent):
    NAME = 'redmine'
    MAINTAINER = 'Romain Bignon'
    EMAIL = 'romain@weboob.org'
    VERSION = '0.8.5'
    DESCRIPTION = 'The Redmine project management web application'
    LICENSE = 'AGPLv3+'
    CONFIG = ValuesDict(Value('url',      label='URL of the Redmine website'),
                        Value('username', label='Login'),
                        Value('password', label='Password', masked=True))
    BROWSER = RedmineBrowser

    def create_default_browser(self):
        return self.create_browser(self.config['url'], self.config['username'], self.config['password'])

    def id2path(self, id):
        return id.split('/', 2)

    def get_content(self, id):
        if isinstance(id, basestring):
            content = Content(id)
        else:
            content = id
            id = content.id

        try:
            _type, project, page = self.id2path(id)
        except ValueError:
            return None

        with self.browser:
            data = self.browser.get_wiki_source(project, page)

        content.content = data
        return content

    def push_content(self, content, message=None, minor=False):
        try:
            _type, project, page = self.id2path(content.id)
        except ValueError:
            return

        with self.browser:
            return self.browser.set_wiki_source(project, page, content.content, message)

    def get_content_preview(self, content):
        try:
            _type, project, page = self.id2path(content.id)
        except ValueError:
            return

        with self.browser:
            return self.browser.get_wiki_preview(project, page, content.content)

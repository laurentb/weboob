# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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

from weboob.capabilities.subtitle import CapSubtitle, LanguageNotSupported
from weboob.tools.backend import Module
from weboob.tools.compat import quote_plus

from .browser import TvsubtitlesBrowser, LANGUAGE_LIST


__all__ = ['TvsubtitlesModule']


class TvsubtitlesModule(Module, CapSubtitle):
    NAME = 'tvsubtitles'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.3'
    DESCRIPTION = 'Tvsubtitles subtitle website'
    LICENSE = 'AGPLv3+'
    BROWSER = TvsubtitlesBrowser

    def get_subtitle(self, id):
        return self.browser.get_subtitle(id)

    def get_subtitle_file(self, id):
        subtitle = self.browser.get_subtitle(id)
        if not subtitle:
            return None

        return self.browser.openurl(subtitle.url.encode('utf-8')).read()

    def iter_subtitles(self, language, pattern):
        if language not in LANGUAGE_LIST:
            raise LanguageNotSupported()
        return self.browser.iter_subtitles(language, quote_plus(pattern.encode('utf-8')))

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
from weboob.applications.suboob.suboob import LANGUAGE_CONV
from weboob.tools.backend import Module
from weboob.tools.compat import quote_plus

from .browser import PodnapisiBrowser


__all__ = ['PodnapisiModule']


class PodnapisiModule(Module, CapSubtitle):
    NAME = 'podnapisi'
    MAINTAINER = u'Julien Veyssier'
    EMAIL = 'julien.veyssier@aiur.fr'
    VERSION = '1.5'
    DESCRIPTION = 'Podnapisi movies and tv series subtitle website'
    LICENSE = 'AGPLv3+'
    BROWSER = PodnapisiBrowser

    def get_subtitle_file(self, id):
        return self.browser.get_file(id)

    def get_subtitle(self, id):
        return self.browser.get_subtitle(id)

    def iter_subtitles(self, language, pattern):
        if language not in list(LANGUAGE_CONV.keys()):
            raise LanguageNotSupported()
        return self.browser.iter_subtitles(language, quote_plus(pattern.encode('utf-8')))

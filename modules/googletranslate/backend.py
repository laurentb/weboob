# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
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
"backend for http://translate.google.com"


from weboob.capabilities.translate import ICapTranslate, Translation, TranslationFail
from weboob.tools.backend import BaseBackend

from .browser import GoogleTranslateBrowser


__all__ = ['GoogleTranslateBackend']


class GoogleTranslateBackend(BaseBackend, ICapTranslate):
    MAINTAINER = 'Lucien Loiseau'
    EMAIL = 'loiseau.lucien@gmail.com'
    VERSION = '0.c'
    LICENSE = 'AGPLv3+'
    NAME = 'googletranslate'
    DESCRIPTION = u'Google translation web service'
    BROWSER = GoogleTranslateBrowser

    def translate(self, lan_from, lan_to, text):
        translation = Translation(0)
        translation.lang_src = lan_from
        translation.lang_dst = lan_to
        translation.text = self.browser.translate(lan_from, lan_to, text)

        if translation.text is None:
            raise TranslationFail()

        return translation

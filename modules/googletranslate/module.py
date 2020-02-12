# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lucien Loiseau
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
"backend for http://translate.google.com"

from __future__ import unicode_literals

from weboob.capabilities.translate import CapTranslate, Translation, TranslationFail, LanguageNotSupported
from weboob.capabilities.base import empty
from weboob.tools.backend import Module

from .browser import GoogleTranslateBrowser


__all__ = ['GoogleTranslateModule']


class GoogleTranslateModule(Module, CapTranslate):
    MAINTAINER = u'Lucien Loiseau'
    EMAIL = 'loiseau.lucien@gmail.com'
    VERSION = '2.0'
    LICENSE = 'AGPLv3+'
    NAME = 'googletranslate'
    DESCRIPTION = u'Google translation web service'
    BROWSER = GoogleTranslateBrowser
    GOOGLELANGUAGE = [
        'ar',
        'af',
        'sq',
        'hy',
        'az',
        'eu',
        'be',
        'bn',
        'bg',
        'ca',
        'zh-CN',
        'hr',
        'cs',
        'da',
        'nl',
        'en',
        'eo',
        'et',
        'tl',
        'fi',
        'fr',
        'gl',
        'ka',
        'de',
        'el',
        'gu',
        'ht',
        'iw',
        'hi',
        'hu',
        'is',
        'id',
        'ga',
        'it',
        'ja',
        'kn',
        'ko',
        'la',
        'lv',
        'lt',
        'mk',
        'ms',
        'mt',
        'no',
        'fa',
        'pl',
        'pt',
        'ro',
        'ru',
        'sr',
        'sk',
        'sl',
        'es',
        'sw',
        'sv',
        'ta',
        'te',
        'th',
        'tr',
        'uk',
        'ur',
        'vi',
        'cy',
        'yi',
    ]

    def translate(self, lan_from, lan_to, text):
        if lan_from not in self.GOOGLELANGUAGE:
            raise LanguageNotSupported()

        if lan_to not in self.GOOGLELANGUAGE:
            raise LanguageNotSupported()

        translation = Translation(0)
        translation.lang_src = lan_from
        translation.lang_dst = lan_to
        translation.text = self.browser.translate(lan_from, lan_to, text)

        if empty(translation.text):
            raise TranslationFail()

        return translation

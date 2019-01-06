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

from __future__ import unicode_literals

from weboob.capabilities.translate import CapTranslate, Translation, TranslationFail, LanguageNotSupported
from weboob.capabilities.base import empty
from weboob.tools.backend import Module

from .browser import GoogleTranslateBrowser


__all__ = ['GoogleTranslateModule']


class GoogleTranslateModule(Module, CapTranslate):
    MAINTAINER = u'Lucien Loiseau'
    EMAIL = 'loiseau.lucien@gmail.com'
    VERSION = '1.5'
    LICENSE = 'AGPLv3+'
    NAME = 'googletranslate'
    DESCRIPTION = u'Google translation web service'
    BROWSER = GoogleTranslateBrowser
    GOOGLELANGUAGE = {
        'Arabic': 'ar',
        'Afrikaans': 'af',
        'Albanian': 'sq',
        'Armenian': 'hy',
        'Azerbaijani': 'az',
        'Basque': 'eu',
        'Belarusian': 'be',
        'Bengali': 'bn',
        'Bulgarian': 'bg',
        'Catalan': 'ca',
        'Chinese': 'zh-CN',
        'Croatian': 'hr',
        'Czech': 'cs',
        'Danish': 'da',
        'Dutch': 'nl',
        'English': 'en',
        'Esperanto': 'eo',
        'Estonian': 'et',
        'Filipino': 'tl',
        'Finnish': 'fi',
        'French': 'fr',
        'Galician': 'gl',
        'Georgian': 'ka',
        'German': 'de',
        'Greek': 'el',
        'Gujarati': 'gu',
        'Haitian': 'ht',
        'Hebrew': 'iw',
        'Hindi': 'hi',
        'Hungaric': 'hu',
        'Icelandic': 'is',
        'Indonesian': 'id',
        'Irish': 'ga',
        'Italian': 'it',
        'Japanese': 'ja',
        'Kannada': 'kn',
        'Korean': 'ko',
        'Latin': 'la',
        'Latvian': 'lv',
        'Lithuanian': 'lt',
        'Macedonian': 'mk',
        'Malay': 'ms',
        'Maltese': 'mt',
        'Norwegian': 'no',
        'Persian': 'fa',
        'Polish': 'pl',
        'Portuguese': 'pt',
        'Romanian': 'ro',
        'Russian': 'ru',
        'Serbian': 'sr',
        'Slovak': 'sk',
        'Slovenian': 'sl',
        'Spanish': 'es',
        'Swahili': 'sw',
        'Swedish': 'sv',
        'Tamil': 'ta',
        'Telugu': 'te',
        'Thai': 'th',
        'Turkish': 'tr',
        'Ukrainian': 'uk',
        'Urdu': 'ur',
        'Vietnamese': 'vi',
        'Welsh': 'cy',
        'Yiddish': 'yi',
        }

    def translate(self, lan_from, lan_to, text):
        if lan_from not in self.GOOGLELANGUAGE.keys():
            raise LanguageNotSupported()

        if lan_to not in self.GOOGLELANGUAGE.keys():
            raise LanguageNotSupported()

        translation = Translation(0)
        translation.lang_src = self.GOOGLELANGUAGE[lan_from]
        translation.lang_dst = self.GOOGLELANGUAGE[lan_to]
        translation.text = self.browser.translate(self.GOOGLELANGUAGE[lan_from], self.GOOGLELANGUAGE[lan_to], text)

        if empty(translation.text):
            raise TranslationFail()

        return translation

# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Romain Bignon
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


class TokenExtractor(object):
    """ Extracts texts token from an HTML document """

    def __init__(self):
        self.iterated_elements = []

    def clear(self):
        """
        Reset any content stored within a TokenExtractor object. Useful to start
        a new parsing without creating a new instance.
        """
        self.iterated_elements = []

    def element_iterated_already(self, html_element):
        if html_element in self.iterated_elements:
            return True
        for ancestor in html_element.iterancestors():
            if ancestor in self.iterated_elements:
                return True
        return False

    def extract_tokens(self, html_element):
        if self.element_iterated_already(html_element):
            return
        self.iterated_elements.append(html_element)
        for text in html_element.itertext():
            text = text.replace(u'\xa0', ' ')
            text = text.replace("\n", ' ')
            for token in self.split_text_into_smaller_tokens(text):
                if self.token_looks_relevant(token):
                    yield token.strip()

    @staticmethod
    def split_text_into_smaller_tokens(text):
        for subtext1 in text.split('\t'):
            yield subtext1

    @staticmethod
    def token_looks_relevant(token):
        return len(token.strip()) > 1

# -*- coding: utf-8 -*-

# Copyright(C) 2017      Vincent A
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

from __future__ import unicode_literals

import re
from ast import literal_eval

import lxml.html

from weboob.browser.pages import HTMLPage, RawPage
from weboob.browser.elements import ItemElement, method
from weboob.browser.filters.standard import CleanText
from weboob.capabilities.messages import Message


class DatePage(RawPage):
    def get_articles(self):
        data = literal_eval(re.search(r',(\{.*\})\);', self.doc.decode('utf-8')).group(1))
        return data['posts']


class IndexPage(HTMLPage):
    def get_dates(self):
        found = False
        for url in self.doc.xpath('//a[@class="post-count-link"]/@href'):
            if self.browser.date.match(url):
                found = True
                yield url

        if found:
            return

        for url in self.doc.xpath('//li[@class="archivedate"]/a/@href'):
            if self.browser.date.match(url):
                yield url


class ArticlePage(HTMLPage):
    @method
    class get_message(ItemElement):
        klass = Message

        obj_title = CleanText('//h3[has-class("post-title")]')
        obj_sender = CleanText('//span[has-class("post-author")]')

        def obj_content(self):
            return lxml.html.tostring(self.xpath('//div[has-class("post-body")]')[0])

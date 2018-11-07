# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

from __future__ import unicode_literals

from datetime import datetime, timedelta

from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.collection import Collection

from weboob.browser.pages import HTMLPage, JsonPage
from weboob.browser.elements import ItemElement, ListElement, method, DictElement
from weboob.browser.filters.standard import CleanText, Regexp, Format, Field, Eval
from weboob.browser.filters.html import CleanHTML
from weboob.browser.filters.json import Dict


def parse_duration(text):
    return timedelta(seconds=int(text) * 60)


class SearchPage(JsonPage):
    @method
    class iter_videos(DictElement):
        item_xpath = 'results/0/hits'

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Format(r"https://www.france.tv/%s/%s-%s.html", Dict('path'), Dict('id'), Dict('url_page'))

            obj_title = CleanText(Dict('title'))
            obj_thumbnail = Eval(Thumbnail,
                                 Format(r'https://www.france.tv%s',
                                        Dict('image/formats/vignette_16x9/urls/w:1024')))

            def obj_date(self):
                return datetime.fromtimestamp(Dict('dates/first_publication_date')(self))

            def obj_duration(self):
                return timedelta(seconds=Dict('duration')(self))


class HomePage(HTMLPage):

    def get_params(self):
        a = Regexp(CleanText('//script'),
                   '"algolia_app_id":"(.*)","algolia_api_key":"(.*)","algolia_api_index_taxonomy".*',
                   '\\1|\\2')(self.doc)
        return a.split('|')

    @method
    class iter_categories(ListElement):
        ignore_duplicate = True

        item_xpath = '//li[has-class("nav-item")]/a'

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return Regexp(CleanText('./@href'), '//www.france.tv/(.*)', default=False)(self)

            def obj_id(self):
                id = Regexp(CleanText('./@href',
                                      replace=[('.html', '-video/')]),
                            '//www.france.tv/(.*)', "\\1",
                            default=None)(self)
                return id[:-1]

            obj_title = CleanText('.')

            def obj_split_path(self):
                return Field('id')(self).split('/')

    @method
    class iter_videos(ListElement):
        def parse(self, el):
            self.item_xpath = u'//a[@data-video]'

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Format('https:%s', CleanText('./@href'))
            obj_title = CleanText(CleanHTML('./div[@class="card-content"]|./div[has-class("card-content")]'))

            def condition(self):
                return Field('title')(self)

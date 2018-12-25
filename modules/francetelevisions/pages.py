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
from weboob.browser.filters.standard import CleanText, Regexp, Format, Field, Env
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

            obj_id = Format(r"https://www.france.tv/%s/%s-%s.html",
                            Dict('path'),
                            Dict('id'),
                            Dict('url_page'))

            obj_title = CleanText(Dict('title'))

            def obj_thumbnail(self):
                try:
                    img = Dict('image/formats/vignette_16x9/urls/w:1024', default=None)(self)

                except KeyError:
                    img = Dict('image/formats/carre/urls/w:400')(self)

                return Thumbnail(r'https://www.france.tv%s' % img)

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

        item_xpath = '//ul[has-class("c-sub-nav-items--channels")]/li/a'

        class item(ItemElement):
            klass = Collection

            def condition(self):
                return CleanText('./@href')(self)[-1] == '/'

            def obj_id(self):
                id = CleanText('./@href')(self)
                return id[1:-1]

            obj_title = CleanText('.')

            def obj_split_path(self):
                return Field('id')(self).split('/')

    @method
    class iter_subcategories(ListElement):
        ignore_duplicate = True

        item_xpath = '//li[@class="c-shortcuts-ctn__replays-links-items"]/a'

        class item(ItemElement):
            klass = Collection

            def condition(self):
                cat = Env('cat')(self)
                return Regexp(CleanText('./@href'), '/%s/.*' % cat, default=False)(self)

            def obj_id(self):
                id = CleanText('./@href', replace=[('.html', '/'),
                                                   ('https://www.france.tv', '')])(self)
                return id[1:-1].split('/')[-1]

            obj_title = CleanText('.')

            def obj_split_path(self):
                return [Env('cat')(self)] + [Field('id')(self)]

    @method
    class iter_emissions(ListElement):
        ignore_duplicate = True

        item_xpath = u'//a[@class="c-card-program__link"]'

        class item(ItemElement):
            klass = Collection

            def condition(self):
                cat = Env('cat')(self)
                return Regexp(CleanText('./@href'), '/%s/.*' % cat[0], default=False)(self)

            def obj_id(self):
                id = CleanText('./@href')(self)
                return id.split('/')[-1]

            obj_title = CleanText('./@title')

            def obj_split_path(self):
                return Env('cat')(self) + [Field('id')(self)]

    @method
    class iter_videos(ListElement):
        item_xpath = u'//h3[@class="c-card-video__infos"]/a'

        class item(ItemElement):
            klass = BaseVideo

            obj_id = Format('https://www.france.tv%s', CleanText('./@href'))
            obj_title = CleanText(CleanHTML('./div[has-class("c-card-video__title")]'))

            def condition(self):
                return Field('title')(self)

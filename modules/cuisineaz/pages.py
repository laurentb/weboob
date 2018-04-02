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


from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage, Thumbnail
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, method, ListElement
from weboob.browser.filters.standard import (
    CleanText, Regexp, Env, Time, Join, Format, Eval,
)
from weboob.browser.filters.html import XPath

import re
import datetime


class CuisineazDuration(Time):
    klass = datetime.timedelta
    _regexp = re.compile(r'((?P<hh>\d+) h)?((?P<mm>\d+) min)?(?P<ss>\d+)?')
    kwargs = {'hours': 'hh', 'minutes': 'mm', 'seconds': 'ss'}


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """

    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//div[@id="divRecette"]'

        def next_page(self):
            next = CleanText('//li[@class="next"]/span/a/@href',
                             default=None)(self)
            if next:
                return next

        class item(ItemElement):
            klass = Recipe

            def condition(self):
                return Regexp(CleanText('./div/h2/a/@href'),
                              '/recettes/(.*).aspx',
                              default=None)(self.el)

            obj_id = Regexp(CleanText('./div/h2/a/@href'),
                            '/recettes/(.*).aspx')
            obj_title = CleanText('./div/h2/a')

            class obj_picture(ItemElement):
                klass = BaseImage

                url = CleanText('./div[has-class("searchImg")]/span/img[@data-src!=""]/@data-src|./div[has-class("searchImg")]/div/span/img[@src!=""]/@src',
                                default=None)
                obj_thumbnail = Eval(Thumbnail, Format('http:%s', url))

                def validate(self, obj):
                    return obj.thumbnail.url != 'http:'

            obj_short_description = CleanText('./div[has-class("show-for-medium")]')


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """
    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('_id')
        obj_title = CleanText('//h1')

        class obj_picture(ItemElement):
            klass = BaseImage

            obj_url = Format('http:%s',
                             CleanText('//img[@id="shareimg" and @src!=""]/@src', default=None))
            obj_thumbnail = Eval(Thumbnail, obj_url)

            def validate(self, obj):
                return obj.url != 'http:'

        def obj_preparation_time(self):
            _prep = CuisineazDuration(CleanText('//span[@id="ContentPlaceHolder_LblRecetteTempsPrepa"]'))(self)
            return int(_prep.total_seconds() / 60)

        def obj_cooking_time(self):
            _cook = CuisineazDuration(CleanText('//span[@id="ContentPlaceHolder_LblRecetteTempsCuisson"]'))(self)
            return int(_cook.total_seconds() / 60)

        def obj_nb_person(self):
            nb_pers = CleanText('//span[@id="ContentPlaceHolder_LblRecetteNombre"]')(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            ingredients = []
            for el in XPath('//section[has-class("recipe_ingredients")]/ul/li')(self):
                ingredients.append(CleanText('.')(el))
            return ingredients

        obj_instructions = Join('\n\n - ', '//div[@id="preparation"]/span/p/text()',
                                addBefore=' - ')

    @method
    class get_comments(ListElement):
        item_xpath = '//div[has-class("comment")]'

        class item(ItemElement):
            klass = Comment

            obj_author = CleanText('./div/div/div/div[@class="author"]')

            obj_text = CleanText('./div/div/p')
            obj_id = CleanText('./@id')

            def obj_rate(self):
                    return len(XPath('.//div/div/div/div/div[@class="icon-star"]')(self))

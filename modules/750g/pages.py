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
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, Filter, DateTime, CleanDecimal
from weboob.browser.filters.html import CleanHTML

from datetime import datetime, date, time


class Time(Filter):
    def filter(self, el):
        _time = DateTime(CleanText(el, replace=[('PT', '')]), default=None)(self)
        if _time:
            _time_ = _time - datetime.combine(date.today(), time(0))
            return _time_.seconds // 60


class ResultsPage(HTMLPage):
    """ Page which contains results as a list of recipies
    """
    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//section[has-class("c-recipe-row")]'

        def next_page(self):
            return CleanText('//li[@class="suivante"]/a/@href')(self)

        class item(ItemElement):
            klass = Recipe

            def condition(self):
                return not CleanText('./div[@class="c-recipe-row__media"]/span[@class="c-recipe-row__video"]/@class',
                                     default=None)(self)

            obj_id = Regexp(CleanText('./div/h2/a/@href'),
                            '/(.*).htm')
            obj_title = CleanText('./div/h2/a')
            obj_thumbnail_url = CleanText('./div/img/@src')
            obj_short_description = CleanText('./div/p')


class RecipePage(HTMLPage):
    """ Page which contains a recipe
    """
    @method
    class get_comments(ListElement):
        item_xpath = '//div[has-class("c-comment__row")]'

        class item(ItemElement):
            klass = Comment

            def validate(self, obj):
                return obj.id

            obj_id = CleanText('./@data-id')
            obj_author = CleanText('./article/div/header/strong/span[@itemprop="author"]')
            obj_text = CleanText('./article/div/div/p')

    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('id')
        obj_title = CleanText('//h1[has-class("fn")]')

        def obj_ingredients(self):
            ingredients = []
            for el in self.page.doc.xpath('//li[@class="ingredient"]'):
                ingredients.append(CleanText('.')(el))
            return ingredients

        obj_cooking_time = Time('//time[@itemprop="cookTime"]/@datetime')
        obj_preparation_time = Time('//time[@itemprop="prepTime"]/@datetime')

        def obj_nb_person(self):
            return [CleanDecimal('//span[@class="yield"]', default=0)(self)]

        obj_instructions = CleanHTML('//div[has-class("c-recipe-steps__item")]')

        obj_picture_url = CleanText('(//img[has-class("c-swiper__media")]/@src)[1]')
        obj_author = Regexp(CleanText('//meta[@name="description"]/@content',
                                      default=''),
                            '.* par (.*)',
                            default=NotAvailable)

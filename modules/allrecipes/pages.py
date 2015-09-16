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


from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.browser.filters.standard import Regexp, CleanText, Env, Duration
from weboob.browser.filters.html import CleanHTML

import re


class CookingDuration(Duration):
    _regexp = re.compile(r'PT((?P<hh>\d+)H)?((?P<mm>\d+)M)?((?P<ss>\d+)S)?')


class ResultsPage(HTMLPage):
    @pagination
    @method
    class iter_recipes(ListElement):
        item_xpath = '//article[@class="grid-col--fixed-tiles"]'

        def next_page(self):
            return CleanText('//button[@id="btnMoreResults"]/@href')(self)

        class item(ItemElement):
            klass = Recipe

            obj_id = Regexp(CleanText('./a[1]/@href'),
                            '/recipe/(.*)/')
            obj_title = CleanText('./a/h3')
            obj_short_description = CleanText('./a/div/div[@class="rec-card__description"]')


class RecipePage(HTMLPage):
    @method
    class get_recipe(ItemElement):
        klass = Recipe

        obj_id = Env('_id')
        obj_title = CleanText('//h1[@itemprop="name"]')

        def obj_preparation_time(self):
            dt = CookingDuration(CleanText('//time[@itemprop="prepTime"]/@datetime'))(self)
            return int(dt.total_seconds() / 60)

        def obj_cooking_time(self):
            dt = CookingDuration(CleanText('//time[@itemprop="cookTime"]/@datetime'))(self)
            return int(dt.total_seconds() / 60)

        def obj_nb_person(self):
            nb_pers = CleanText('//meta[@id="metaRecipeServings"]/@content')(self)
            return [nb_pers] if nb_pers else NotAvailable

        def obj_ingredients(self):
            ingredients = []
            for el in self.el.xpath('//ul[has-class("checklist")]/li/label/span[@itemprop="ingredients"]'):
                ing = CleanText('.')(el)
                if ing:
                    ingredients.append(ing)
            return ingredients

        obj_instructions = CleanHTML('//ol[@itemprop="recipeInstructions"]')
        obj_thumbnail_url = CleanText('//section[has-class("hero-photo")]/span/a/img/@src')

        obj_picture_url = CleanText('//section[has-class("hero-photo")]/span/a/img/@src')

    @method
    class get_comments(ListElement):
        item_xpath = '//div[@itemprop="review"]'
        ignore_duplicate = True

        class item(ItemElement):
            klass = Comment

            obj_author = CleanText('./article/a/div/a/ul/li/h4[@itemprop="author"]')
            obj_rate = CleanText('./article/div/div[@class="rating-stars"]/@data-ratingstars')
            obj_text = CleanText('./p[@itemprop="reviewBody"]')
            obj_id = CleanText('./article/a/@href')

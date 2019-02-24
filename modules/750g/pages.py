# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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


from weboob.capabilities.recipe import Recipe, Comment
from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage, Thumbnail
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import ItemElement, ListElement, method
from weboob.browser.filters.standard import CleanText, Regexp, Env, CleanDecimal, Eval
from weboob.browser.filters.json import Dict, NotFound
from datetime import datetime, date, time
from dateutil.parser import parse as parse_date
from weboob.tools.json import json


class Time(Dict):
    def filter(self, el):
        if el and not isinstance(el, NotFound):
            el = el.replace('PT', '')
            if el == u'P':
                return NotAvailable
            _time = parse_date(el, dayfirst=False, fuzzy=False)
            _time = _time - datetime.combine(date.today(), time(0))
            return _time.seconds // 60


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
                                     default=None)(self) and CleanText('./div/h2/a/@href')(self)

            obj_id = Regexp(CleanText('./div/h2/a/@href'),
                            '/(.*).htm')

            obj_title = CleanText('./div/h2/a')

            class obj_picture(ItemElement):
                klass = BaseImage

                obj_thumbnail = Eval(Thumbnail, CleanText('./div/img/@src'))

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

        def parse(self, el):
            json_content = CleanText('//head/script[@type="application/ld+json"]')(el)
            self.el = json.loads(json_content)

        obj_id = Env('id')
        obj_title = Dict('name')
        obj_ingredients = Dict('recipeIngredient')
        obj_cooking_time = Time('cookTime')
        obj_preparation_time = Time('prepTime')

        def obj_nb_person(self):
            return [CleanDecimal(Dict('recipeYield'), default=0)(self)]

        obj_instructions = Dict('recipeInstructions')
        obj_author = Dict('author/name', default=NotAvailable)

        def obj_picture(self):
            img = BaseImage()
            try:
                img.url = self.el['image']
            except KeyError:
                return
            return img

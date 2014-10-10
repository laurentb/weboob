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


from weboob.capabilities.recipe import Recipe
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.deprecated.browser import Page

import string


class ResultsPage(Page):
    """ Page which contains results as a list of recipies
    """

    def iter_recipes(self):
        for div in self.parser.select(self.document.getroot(), 'div.result-recipe'):
            thumbnail_url = NotAvailable
            short_description = NotAvailable
            imgs = self.parser.select(div, 'a.pull-image-left img')
            if len(imgs) > 0:
                url = unicode(imgs[0].attrib.get('src', ''))
                if url.startswith('http://'):
                    thumbnail_url = url

            link = self.parser.select(div, 'div.result-text a', 1)
            title = unicode(link.text)
            id = unicode(link.attrib.get('href', '').split('/')[2])

            txt = self.parser.select(div, 'div.result-text p', 1)
            short_description = unicode(txt.text_content())

            recipe = Recipe(id, title)
            recipe.thumbnail_url = thumbnail_url
            recipe.short_description = short_description
            recipe.instructions = NotLoaded
            recipe.ingredients = NotLoaded
            recipe.nb_person = NotLoaded
            recipe.cooking_time = NotLoaded
            recipe.preparation_time = NotLoaded
            recipe.author = NotLoaded
            yield recipe


class RecipePage(Page):
    """ Page which contains a recipe
    """

    def get_recipe(self, id):
        title = NotAvailable
        preparation_time = NotAvailable
        cooking_time = NotAvailable
        author = NotAvailable
        nb_person = NotAvailable
        ingredients = NotAvailable
        picture_url = NotAvailable
        instructions = NotAvailable
        comments = NotAvailable

        title = unicode(self.parser.select(self.document.getroot(), 'h1 span[property$=name]', 1).text)
        main = self.parser.select(self.document.getroot(), 'div[typeof$=Recipe]', 1)
        imgillu = self.parser.select(main, 'div.image-with-credit img')
        if len(imgillu) > 0:
            picture_url = unicode(imgillu[0].attrib.get('src', ''))

        l_spanprep = self.parser.select(self.document.getroot(), 'span.preptime[property$=prepTime]')
        if len(l_spanprep) > 0:
            preparation_time = 0
            prep = l_spanprep[0].attrib.get('content','')
            if 'H' in prep:
                preparation_time += 60 * (int(prep.split('PT')[-1].split('H')[0]))
            if 'M' in prep:
                preparation_time += int(prep.split('PT')[-1].split('H')[-1].split('M')[0])
        l_cooktime = self.parser.select(main, 'span.cooktime[property$=cookTime]')
        if len(l_cooktime) > 0:
            cooking_time = 0
            cook = l_cooktime[0].attrib.get('content','')
            if 'H' in cook:
                cooking_time += 60 * (int(cook.split('PT')[-1].split('H')[0]))
            if 'M' in cook:
                cooking_time += int(cook.split('PT')[-1].split('H')[-1].split('M')[0])
        l_nbpers = self.parser.select(main, 'div.ingredients p.servings')
        if len(l_nbpers) > 0:
            rawnb = l_nbpers[0].text.strip(string.letters+' ')
            if '/' in rawnb:
                nbs = rawnb.split('/')
                nb_person = [int(nbs[0]), int(nbs[1])]
            else:
                nb_person = [int(rawnb)]

        ingredients = []
        l_ing = self.parser.select(main, 'div.ingredients ul.dotlist')
        for ing in l_ing:
            sublists = self.parser.select(ing, 'li')
            for i in sublists:
                ingtxt = unicode(i.text_content().strip())
                if ingtxt != '':
                    ingredients.append(' '.join(ingtxt.split()))

        instructions = u''
        num_inst = 1
        l_divinst = self.parser.select(self.document.getroot(), 'div#recipe-steps-list p.step-details')
        for inst in l_divinst:
            instructions += '%s: %s\n' % (num_inst, inst.text_content())
            num_inst += 1

        recipe = Recipe(id, title)
        recipe.preparation_time = preparation_time
        recipe.cooking_time = cooking_time
        recipe.nb_person = nb_person
        recipe.ingredients = ingredients
        recipe.instructions = instructions
        recipe.picture_url = picture_url
        recipe.comments = comments
        recipe.author = author
        recipe.thumbnail_url = NotLoaded
        return recipe

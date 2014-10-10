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


class FourOFourPage(Page):
    pass


class ResultsPage(Page):
    """ Page which contains results as a list of recipies
    """

    def iter_recipes(self):
        for div in self.parser.select(self.document.getroot(), 'div.recipe-info'):
            thumbnail_url = NotAvailable
            short_description = NotAvailable
            imgs = self.parser.select(div.getparent(), 'img')
            if len(imgs) > 0:
                url = unicode(imgs[0].attrib.get('src', ''))
                if url.startswith('http://'):
                    thumbnail_url = url

            link = self.parser.select(div, 'a.title', 1)
            title = unicode(link.text)
            id = unicode(link.attrib.get('href', '').split('/')[2])

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

        title = unicode(self.parser.select(self.document.getroot(), 'h1#itemTitle', 1).text)
        imgillu = self.parser.select(self.document.getroot(), 'img#imgPhoto')
        if len(imgillu) > 0:
            picture_url = unicode(imgillu[0].attrib.get('src', ''))

        ingredients = []
        l_ing = self.parser.select(self.document.getroot(), 'li#liIngredient')
        for ing in l_ing:
            ingtxt = unicode(ing.text_content().strip())
            if ingtxt != '':
                ingredients.append(ingtxt)

        instructions = u''
        l_divinst = self.parser.select(self.document.getroot(), 'div.directLeft li')
        num_instr = 1
        for inst in l_divinst:
            instructions += '%s: %s\n' % (num_instr, inst.text_content())
            num_instr += 1

        prepmin = 0
        emprep = self.parser.select(self.document.getroot(), 'span#prepHoursSpan em')
        if len(emprep) > 0:
            prepmin += int(emprep[0].text) * 60
        emprep = self.parser.select(self.document.getroot(), 'span#prepMinsSpan em')
        if len(emprep) > 0:
            prepmin += int(emprep[0].text)
        if prepmin != 0:
            preparation_time = prepmin
        cookmin = 0
        emcooktime = self.parser.select(self.document.getroot(), 'span#cookHoursSpan em')
        if len(emcooktime) > 0:
            cookmin += int(emcooktime[0].text) * 60
        emcooktime = self.parser.select(self.document.getroot(), 'span#cookMinsSpan em')
        if len(emcooktime) > 0:
            cookmin += int(emcooktime[0].text)
        if cookmin != 0:
            cooking_time = cookmin
        l_nbpers = self.parser.select(self.document.getroot(), 'span#lblYield[itemprop=recipeYield]')
        if len(l_nbpers) > 0 and 'servings' in l_nbpers[0].text:
            nb_person = [int(l_nbpers[0].text.split()[0])]

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

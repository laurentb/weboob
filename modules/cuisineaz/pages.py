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
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.deprecated.browser import Page


class ResultsPage(Page):
    """ Page which contains results as a list of recipies
    """

    def iter_recipes(self):
        for div in self.parser.select(self.document.getroot(), 'div.rechRecette'):
            thumbnail_url = NotAvailable
            short_description = NotAvailable
            imgs = self.parser.select(div, 'img')
            if len(imgs) > 0:
                url = unicode(imgs[0].attrib.get('src', ''))
                if url.startswith('http://'):
                    thumbnail_url = url

            link = self.parser.select(div, 'a.rechRecetTitle', 1)
            title = unicode(link.text)
            id = unicode(link.attrib.get('href', '').split(
                '/')[-1].replace('.aspx', ''))

            short_description = u''
            ldivprix = self.parser.select(div, 'div.prix')
            if len(ldivprix) > 0:
                divprix = ldivprix[0]
                nbprixneg = 0
                spanprix = self.parser.select(divprix, 'span')
                if len(spanprix) > 0:
                    nbprixneg = unicode(spanprix[0].text).count(u'€')
                nbprixtot = unicode(divprix.text_content()).count(u'€')
                short_description += u'Cost: %s/%s ; ' % (
                    nbprixtot - nbprixneg, nbprixtot)

            short_description += unicode(' '.join(self.parser.select(
                div, 'div.rechResume', 1).text_content().split()).strip()).replace(u'€', '')
            short_description += u' '
            short_description += unicode(' '.join(self.parser.select(
                div, 'div.rechIngredients', 1).text_content().split()).strip())

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

        title = unicode(self.parser.select(
            self.document.getroot(), 'div#ficheRecette h1.fn.recetteH1', 1).text)
        main = self.parser.select(
            self.document.getroot(), 'div#ficheRecette', 1)
        imgillu = self.parser.select(main, 'div#recetteLeft img.photo')
        if len(imgillu) > 0:
            picture_url = unicode(imgillu[0].attrib.get('src', ''))

        l_spanprep = self.parser.select(main, 'span.preptime')
        if len(l_spanprep) > 0:
            preparation_time = int(self.parser.tocleanstring(l_spanprep[0]).split()[0])
        l_cooktime = self.parser.select(main, 'span.cooktime')
        if len(l_cooktime) > 0:
            cooking_time = int(self.parser.tocleanstring(l_cooktime[0]).split()[0])
        l_nbpers = self.parser.select(main, 'td#recipeQuantity span')
        if len(l_nbpers) > 0:
            rawnb = l_nbpers[0].text.split()[0]
            if '/' in rawnb:
                nbs = rawnb.split('/')
                nb_person = [int(nbs[0]), int(nbs[1])]
            else:
                nb_person = [int(rawnb)]

        ingredients = []
        l_ing = self.parser.select(main, 'div#ingredients li.ingredient')
        for ing in l_ing:
            ingtxt = unicode(ing.text_content().strip())
            if ingtxt != '':
                ingredients.append(ingtxt)

        instructions = u''
        l_divinst = self.parser.select(
            main, 'div#preparation span.instructions div')
        for inst in l_divinst:
            instructions += '%s: ' % inst.text
            instructions += '%s\n' % inst.getnext().text

        divcoms = self.parser.select(self.document.getroot(), 'div.comment')
        if len(divcoms) > 0:
            comments = []
            for divcom in divcoms:
                author = unicode(self.parser.select(
                    divcom, 'div.commentAuthor span', 1).text)
                comtxt = unicode(self.parser.select(
                    divcom, 'p', 1).text_content().strip())
                comments.append(Comment(author=author, text=comtxt))

        spans_author = self.parser.select(self.document.getroot(), 'span.author')
        if len(spans_author) > 0:
            author = unicode(spans_author[0].text_content().strip())

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

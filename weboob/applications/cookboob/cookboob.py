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

from __future__ import with_statement

import sys

from weboob.capabilities.recipe import ICapRecipe
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.tools.application.repl import ReplApplication
from weboob.tools.application.formatters.iformatter import IFormatter, PrettyFormatter


__all__ = ['Cookboob']


class RecipeInfoFormatter(IFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'preparation_time', 'cooking_time', 'ingredients', 'instructions', 'nb_person', 'comments')

    def format_obj(self, obj, alias):
        result = u'%s%s%s\n' % (self.BOLD, obj.title, self.NC)
        result += 'ID: %s\n' % obj.fullid
        result += 'Preparation time: %s\n' % obj.preparation_time
        result += 'Cooking time: %s\n' % obj.cooking_time
        result += 'Amount of people: %s\n' % obj.nb_person
        result += '\n%sIngredients%s\n' % (self.BOLD, self.NC)
        for i in obj.ingredients:
            result += '  * %s\n'%i
        result += '\n%sInstructions%s\n' % (self.BOLD, self.NC)
        result += '%s\n'%obj.instructions
        result += '\n%sComments%s\n' % (self.BOLD, self.NC)
        for c in obj.comments:
            result += '  * %s\n'%c
        return result


class RecipeListFormatter(PrettyFormatter):
    MANDATORY_FIELDS = ('id', 'title', 'short_description', 'preparation_time')

    def get_title(self, obj):
        return obj.title

    def get_description(self, obj):
        result = u''
        if obj.preparation_time != NotAvailable and obj.preparation_time != NotLoaded:
            result += 'prep time: %smin'%obj.preparation_time
        if obj.short_description != NotAvailable:
            result += 'description: %s\n'%obj.short_description
        return result


class Cookboob(ReplApplication):
    APPNAME = 'cookboob'
    VERSION = '0.f'
    COPYRIGHT = 'Copyright(C) 2013 Julien Veyssier'
    DESCRIPTION = "Console application allowing to search for recipes on various websites."
    SHORT_DESCRIPTION = "search and consult recipes"
    CAPS = ICapRecipe
    EXTRA_FORMATTERS = {'recipe_list': RecipeListFormatter,
                        'recipe_info': RecipeInfoFormatter
                       }
    COMMANDS_FORMATTERS = {'search':    'recipe_list',
                           'info':      'recipe_info'
                          }

    def complete_info(self, text, line, *ignored):
        args = line.split(' ')
        if len(args) == 2:
            return self._complete_object()

    def do_info(self, id):
        """
        info ID

        Get information about a recipe.
        """

        recipe = self.get_object(id, 'get_recipe')
        if not recipe:
            print >>sys.stderr, 'Recipe not found: %s' % id
            return 3

        self.start_format()
        self.format(recipe)
        self.flush()

    def do_search(self, pattern):
        """
        search [PATTERN]

        Search recipes.
        """
        self.change_path([u'search'])
        self.start_format(pattern=pattern)
        for backend, recipe in self.do('iter_recipes', pattern=pattern):
            self.cached_format(recipe)
        self.flush()

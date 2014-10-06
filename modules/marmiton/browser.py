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


from weboob.deprecated.browser import Browser, BrowserHTTPNotFound

from .pages import RecipePage, ResultsPage


__all__ = ['MarmitonBrowser']


class MarmitonBrowser(Browser):
    DOMAIN = 'www.marmiton.org'
    PROTOCOL = 'http'
    ENCODING = 'utf-8'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.marmiton.org/recettes/recherche.aspx.*': ResultsPage,
        'http://www.marmiton.org/recettes/recette_.*': RecipePage,
    }

    def iter_recipes(self, pattern):
        self.location('http://www.marmiton.org/recettes/recherche.aspx?st=5&cli=1&aqt=%s' % (pattern))
        assert self.is_on_page(ResultsPage)
        return self.page.iter_recipes()

    def get_recipe(self, id):
        try:
            self.location('http://www.marmiton.org/recettes/recette_%s.aspx' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(RecipePage):
            return self.page.get_recipe(id)

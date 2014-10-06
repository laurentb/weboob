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


__all__ = ['SevenFiftyGramsBrowser']


class SevenFiftyGramsBrowser(Browser):
    DOMAIN = 'www.750g.com'
    PROTOCOL = 'http'
    ENCODING = 'windows-1252'
    USER_AGENT = Browser.USER_AGENTS['wget']
    PAGES = {
        'http://www.750g.com/recettes_.*.htm': ResultsPage,
        'http://www.750g.com/fiche_de_cuisine_complete.htm\?recettes_id=[0-9]*': RecipePage,
    }

    def iter_recipes(self, pattern):
        self.location('http://www.750g.com/recettes_%s.htm' % (pattern.replace(' ', '_')))
        assert self.is_on_page(ResultsPage)
        return self.page.iter_recipes()

    def get_recipe(self, id):
        try:
            self.location('http://www.750g.com/fiche_de_cuisine_complete.htm?recettes_id=%s' % id)
        except BrowserHTTPNotFound:
            return
        if self.is_on_page(RecipePage):
            return self.page.get_recipe(id)

# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from weboob.browser import PagesBrowser, URL

from .pages import ValidationPage, HomePage, HistoryPage, StoryPage, AuthorPage

# Browser


class HDSBrowser(PagesBrowser):
    BASEURL = 'http://histoires-de-sexe.net'

    validation_page = URL('^/$', ValidationPage)
    home = URL(r'/menu.php', HomePage)
    history = URL(r'/sexe/histoires-par-date.php\?p=(?P<pagenum>\d+)', HistoryPage)
    story = URL(r'/sexe.php\?histoire=(?P<id>.+)', StoryPage)
    author = URL(r'/fiche.php\?auteur=(?P<name>.+)', AuthorPage)

    def iter_stories(self):
        n = 1
        self.history.go(pagenum=n)
        while self.page.get_numerous() == n:
            for story in self.page.iter_stories():
                yield story

            n += 1
            self.history.go(pagenum=n)

    def get_story(self, id):
        self.story.go(id=id)

        assert self.story.is_here()
        return self.page.get_story()

    def get_author(self, name):
        self.author.go(name=name)

        assert self.author.is_here()
        return self.page.get_author()

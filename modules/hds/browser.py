# -*- coding: utf-8 -*-

# Copyright(C) 2011  Romain Bignon
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


from weboob.tools.browser import Browser

from .pages import ValidationPage, HomePage, HistoryPage, StoryPage, AuthorPage

# Browser


class HDSBrowser(Browser):
    ENCODING = 'ISO-8859-1'
    DOMAIN = 'histoires-de-sexe.net'
    PAGES = {'http://histoires-de-sexe.net/': ValidationPage,
             'http://histoires-de-sexe.net/menu.php': HomePage,
             'http://histoires-de-sexe.net/sexe/histoires-par-date.php.*': HistoryPage,
             'http://histoires-de-sexe.net/sexe.php\?histoire=(?P<id>.+)': StoryPage,
             'http://histoires-de-sexe.net/fiche.php\?auteur=(?P<name>.+)': AuthorPage,
            }

    def iter_stories(self):
        self.location('/sexe/histoires-par-date.php')
        n = 1
        while self.page.get_numerous() == n:
            count = 0
            for count, story in enumerate(self.page.iter_stories()):
                yield story

            n += 1
            self.location('/sexe/histoires-par-date.php?p=%d' % n)

    def get_story(self, id):
        id = int(id)

        self.location('/sexe.php?histoire=%d' % id)
        assert self.is_on_page(StoryPage)
        return self.page.get_story()

    def get_author(self, name):
        self.location(self.buildurl('/fiche.php', auteur=name.encode('iso-8859-15')))

        assert self.is_on_page(AuthorPage)
        return self.page.get_author()

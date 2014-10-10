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

import re

from weboob.capabilities.subtitle import Subtitle
from weboob.deprecated.browser import Page


class HomePage(Page):
    def iter_subtitles(self, language, pattern):
        self.browser.select_form(nr=0)
        self.browser['q'] = pattern.encode('utf-8')
        self.browser.submit()
        assert self.browser.is_on_page(SearchPage)
        for subtitle in self.browser.page.iter_subtitles(language):
            yield subtitle


class SearchPage(Page):
    """ Page which contains results as a list of series
    """

    def iter_subtitles(self, language):
        list_result = self.parser.select(self.document.getroot(), 'div.left_articles ul')
        if len(list_result) > 0:
            li_result = self.parser.select(list_result[0], 'li')
            for line in li_result:
                if len(self.parser.select(line, 'img[alt=%s]' % language)) > 0:
                    link = self.parser.select(line, 'a', 1)
                    href = link.attrib.get('href', '')
                    self.browser.location("http://%s%s" % (self.browser.DOMAIN, href))
                    assert self.browser.is_on_page(SeriePage)
                    for subtitle in self.browser.page.iter_subtitles(language):
                        yield subtitle


class SeriePage(Page):
    """ Page of all seasons
    """

    def iter_subtitles(self, language, only_one_season=False):
        # handle the current season
        last_table_line = self.parser.select(self.document.getroot(), 'table#table5 tr')[-1]
        amount = int(self.parser.select(last_table_line, 'td')[2].text_content())
        if amount > 0:
            my_lang_img = self.parser.select(last_table_line, 'img[alt=%s]' % language)
            if len(my_lang_img) > 0:
                url_current_season = self.browser.geturl().split('/')[-1].replace(
                    'tvshow', 'subtitle').replace('.html', '-%s.html' % language)
                self.browser.location(url_current_season)
                assert self.browser.is_on_page(SeasonPage)
                yield self.browser.page.iter_subtitles()

        if not only_one_season:
            # handle the other seasons by following top links
            other_seasons_links = self.parser.select(self.document.getroot(), 'p.description a')
            for link in other_seasons_links:
                href = link.attrib.get('href', '')
                self.browser.location("http://%s/%s" % (self.browser.DOMAIN, href))
                assert self.browser.is_on_page(SeriePage)
                for subtitle in self.browser.page.iter_subtitles(language, True):
                    yield subtitle


class SeasonPage(Page):
    """ Page of a season with the right language
    """

    def get_subtitle(self):
        filename_line = self.parser.select(self.document.getroot(), 'img[alt=filename]', 1).getparent().getparent()
        name = unicode(self.parser.select(filename_line, 'td')[2].text)
        id = self.browser.geturl().split('/')[-1].replace('.html', '').replace('subtitle-', '')
        url = unicode('http://%s/download-%s.html' % (self.browser.DOMAIN, id))
        amount_line = self.parser.select(self.document.getroot(), 'tr[title~=amount]', 1)
        nb_cd = int(self.parser.select(amount_line, 'td')[2].text)
        lang = unicode(url.split('-')[-1].split('.html')[0])
        filenames_line = self.parser.select(self.document.getroot(), 'tr[title~=list]', 1)
        file_names = self.parser.select(filenames_line, 'td')[2].text_content().strip().replace('.srt', '.srt\n')
        desc = u"files :\n"
        desc += file_names

        m = re.match('(.*?)\.(\w+)$', name)
        if m:
            name = m.group(1)
            ext = m.group(2)
        else:
            ext = 'zip'

        subtitle = Subtitle(id, name)
        subtitle.url = url
        subtitle.ext = ext
        subtitle.language = lang
        subtitle.nb_cd = nb_cd
        subtitle.description = desc
        return subtitle

    def iter_subtitles(self):
        return self.get_subtitle()

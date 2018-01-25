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

from __future__ import unicode_literals

import re

from weboob.capabilities.subtitle import Subtitle
from weboob.browser.pages import HTMLPage
from weboob.tools.misc import to_unicode


class HomePage(HTMLPage):
    def iter_subtitles(self, language, pattern):
        form = self.get_form(nr=0)
        form['q'] = pattern
        form.submit()
        assert self.browser.search.is_here()
        for subtitle in self.browser.page.iter_subtitles(language):
            yield subtitle


class SearchPage(HTMLPage):
    """ Page which contains results as a list of series
    """

    def iter_subtitles(self, language):
        list_result = self.doc.xpath('//div[has-class("left_articles")]//ul')
        if len(list_result) > 0:
            li_result = list_result[0].xpath('.//li')
            for line in li_result:
                if len(line.xpath('.//img[@alt=$alt]', alt=language)) > 0:
                    link, = line.xpath('.//a')
                    href = link.attrib.get('href', '')
                    self.browser.location("%s%s" % (self.browser.BASEURL, href))
                    assert self.browser.serie.is_here()
                    for subtitle in self.browser.page.iter_subtitles(language):
                        yield subtitle


class SeriePage(HTMLPage):
    """ Page of all seasons
    """

    def iter_subtitles(self, language, only_one_season=False):
        # handle the current season
        last_table_line = self.doc.xpath('//table[@id="table5"]//tr')[-1]
        amount = int(last_table_line.xpath('.//td')[2].text_content())
        if amount > 0:
            my_lang_img = last_table_line.xpath('.//img[@alt=$alt]', alt=language)
            if len(my_lang_img) > 0:
                url_current_season = self.url.split('/')[-1].replace(
                    'tvshow', 'subtitle').replace('.html', '-%s.html' % language)
                self.browser.location(url_current_season)
                assert self.browser.season.is_here()
                yield self.browser.page.iter_subtitles()

        if not only_one_season:
            # handle the other seasons by following top links
            other_seasons_links = self.doc.xpath('//p[has-class("description")]//a')
            for link in other_seasons_links:
                href = link.attrib.get('href', '')
                self.browser.location("%s/%s" % (self.browser.BASEURL, href))
                assert self.browser.serie.is_here()
                for subtitle in self.browser.page.iter_subtitles(language, True):
                    yield subtitle


class SeasonPage(HTMLPage):
    """ Page of a season with the right language
    """

    def get_subtitle(self):
        filename_line = self.doc.xpath('//img[@alt="filename"]')[0].getparent().getparent()
        name = to_unicode(filename_line.xpath('.//td')[2].text)
        id = self.url.split('/')[-1].replace('.html', '').replace('subtitle-', '')
        url = '%s/download-%s.html' % (self.browser.BASEURL, id)
        amount_line, = self.doc.xpath('//tr[contains(@title, "amount")]')
        nb_cd = int(amount_line.xpath('.//td')[2].text)
        lang = url.split('-')[-1].split('.html')[0]
        filenames_line, = self.doc.xpath('//tr[contains(@title,"list")]')
        file_names = filenames_line.xpath('.//td')[2].text_content().strip().replace('.srt', '.srt\n')
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

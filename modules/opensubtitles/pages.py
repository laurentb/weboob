# -*- coding: utf-8 -*-

# Copyright(C) 2013 Julien Veyssier
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
import re

from weboob.capabilities.subtitle import Subtitle
from weboob.browser.pages import HTMLPage, pagination
from weboob.browser.elements import TableElement, ItemElement, method
from weboob.browser.filters.html import Attr, Link, AbsoluteLink
from weboob.browser.filters.standard import Regexp, CleanText, CleanDecimal


class SearchPage(HTMLPage):
    """ Page which contains results as a list of movies
    """
    next_page = Link('.//div[@id="pager"]//div//a[text()=">>"]')

    @pagination
    def iter_subtitles(self):
        results = self.doc.xpath('.//table[@id="search_results"]/tbody/tr[has-class("change")]')
        for el in results:
            url = Link('.//a[has-class("bnone")]')(el)
            self.browser.location(url)
            for sub in self.browser.page.iter_subtitles():
                yield sub


class SubtitlesPage(HTMLPage):
    @method
    class iter_subtitles(TableElement):
        item_xpath = '//table[@id="search_results"]//tbody//tr[has-class("change")]'
        head_xpath = '//table[@id="search_results"]//tbody//tr[has-class("head")]'

        class item(ItemElement):
            klass = Subtitle
            obj_id = Regexp(Attr('.//td[1]', 'id'), 'main(\d*)')
            obj_name = Regexp(
                CleanText('.//td[1]'),
                '(.*)Download at 25'
            )
            obj_nb_cd = CleanDecimal('.//td[3]')
            obj_url = AbsoluteLink('.//td[5]//a')
            obj_language = Regexp(Attr('.//td[2]//a//div', 'class'), 'flag (.*)')


class SubtitlePage(HTMLPage):
    def get_subtitle(self, id=None):
        subtitle = Subtitle()
        subtitle.description = CleanText('.//fieldset/span[@itemprop="description"]')(self.doc)
        if id:
            subtitle.id = id
        else:
            regexp = re.compile('https://www.opensubtitles.org/en/subtitles/(?P<id>\d+)/.*$')
            result = regexp.match(self.url)
            subtitle.id = result.groupdict()['id']

        subtitle.name = CleanText('.//div//div//h2')(self.doc)
        subtitle.url = self.url
        return subtitle

    def iter_subtitles(self):
        return list([self.get_subtitle()])


class SeriesSubtitlePage(HTMLPage):
    def iter_subtitles(self):
        season = ''
        series_name = CleanText('//div[has-class("msg")]//h1//span[@itemprop="name"]')(self.doc)
        # A regexp to recover the sub id from url
        regexp = re.compile('.*/imdbid-(?P<episode_id>\d+)$')
        for sub in self.doc.xpath('//table[@id="search_results"]//tbody//tr[not(contains(@class,"head"))]'):
            if not Attr('.', 'class', default=None)(sub):
                season = CleanText('.//td[1]')(sub)
            else:
                subtitle = Subtitle()
                episode = CleanText('.//td[1]')(sub)
                subtitle.name = '%s - %s - Episode %s' % (series_name, season, episode)
                url = Link('.//td[3]//a')(sub)
                subtitle.url = self.browser.absurl(url)
                result = regexp.match(url)
                subtitle.id = result.groupdict()['episode_id']
                yield subtitle

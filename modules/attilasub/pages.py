# -*- coding: utf-8 -*-

# Copyright(C) 2010-2012 Julien Veyssier
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


try:
    from urlparse import parse_qs
except ImportError:
    from cgi import parse_qs  # NOQA

from urlparse import urlsplit

from weboob.capabilities.subtitle import Subtitle
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage
from weboob.tools.misc import get_bytes_size


__all__ = ['SubtitlesPage','SearchPage']


class SearchPage(BasePage):
    def iter_subtitles(self,pattern):
        fontresult = self.parser.select(self.document.getroot(),'div.search-results font.search-results')
        # for each result in freefind, explore the subtitle list page to iter subtitles
        for res in fontresult:
            a = self.parser.select(res,'a',1)
            url = a.attrib.get('href','')
            self.browser.location(url)
            assert self.browser.is_on_page(SubtitlesPage)
            # subtitles page does the job
            for subtitle in self.browser.page.iter_subtitles(pattern):
                yield subtitle


class SubtitlesPage(BasePage):
    def get_subtitle(self,id):
        href = id.split('|')[1]
        # we have to find the 'tr' which contains the link to this address
        a = self.parser.select(self.document.getroot(),'a[href="%s"]'%href,1)
        line = a.getparent().getparent().getparent().getparent().getparent()
        cols = self.parser.select(line,'td')
        traduced_title = self.parser.select(cols[0],'font',1).text.lower()
        original_title = self.parser.select(cols[1],'font',1).text.lower()

        traduced_title_words = traduced_title.split()
        original_title_words = original_title.split()

        # this is to trash special spacing chars
        traduced_title = " ".join(traduced_title_words)
        original_title = " ".join(original_title_words)

        name = "%s (%s)"%(original_title,traduced_title)
        url = "http://davidbillemont3.free.fr/%s"%href
        subtitle = Subtitle(id,name)
        subtitle.url = url
        subtitle.fps = 0
        subtitle.description = "no desc"
        return subtitle

    def iter_subtitles(self,pattern):
        pattern = pattern.strip().replace('+',' ')
        pattern_words = pattern.split()
        tab = self.parser.select(self.document.getroot(),'table[bordercolor="#B8C0B2"]')
        if len(tab) == 0:
            tab = self.parser.select(self.document.getroot(),'table[bordercolordark="#B8C0B2"]')
            if len(tab) == 0:
                return
        for line in tab[0].getiterator('tr'):
            cols = self.parser.select(line,'td')
            traduced_title = self.parser.select(cols[0],'font',1).text.lower()
            original_title = self.parser.select(cols[1],'font',1).text.lower()

            traduced_title_words = traduced_title.split()
            original_title_words = original_title.split()

            # if the pattern is one word and in the title OR if the 
            # intersection between pattern and the title is at least 2 words
            if (len(pattern_words) == 1 and pattern in traduced_title_words) or\
               (len(pattern_words) == 1 and pattern in original_title_words) or\
               (len(list(set(pattern_words) & set(traduced_title_words))) > 1) or\
               (len(list(set(pattern_words) & set(original_title_words))) > 1):

                # this is to trash special spacing chars
                traduced_title = " ".join(traduced_title_words)
                original_title = " ".join(original_title_words)

                name = "%s (%s)"%(original_title,traduced_title)
                href = self.parser.select(cols[3],'a',1).attrib.get('href','')
                url = "http://davidbillemont3.free.fr/%s"%href
                id = "%s|%s"%(self.browser.geturl().split('/')[-1],href)
                subtitle = Subtitle(id,name)
                subtitle.url = url
                subtitle.fps = 0
                subtitle.description = "no desc"
                yield subtitle

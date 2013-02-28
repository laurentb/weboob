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


from weboob.capabilities.subtitle import Subtitle
from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BasePage


__all__ = ['SubtitlesPage','SubtitlePage','SearchPage']


LANGUAGE_CONV = {
'ar':'ara', 'eo':'epo',  'ga':'',    'ru':'rus',
'af':''   , 'et':'est',  'it':'ita', 'sr':'scc',
'sq':'alb', 'tl':''   ,  'ja':'jpn', 'sk':'slo',
'hy':'arm', 'fi':'fin',  'kn':'',    'sl':'slv',
'az':''   , 'fr':'fre',  'ko':'kor', 'es':'spa',
'eu':'baq', 'gl':'glg',  'la':'',    'sw':'swa',
'be':''   , 'ka':'geo',  'lv':'lav', 'sv':'swe',
'bn':'ben', 'de':'ger',  'lt':'lit', 'ta':'',
'bg':'bul', 'gr':'ell',  'mk':'mac', 'te':'tel',
'ca':'cat', 'gu':''   ,  'ms':'may', 'th':'tha',
'zh':'chi', 'ht':''   ,  'mt':'',    'tr':'tur',
'hr':'hrv', 'iw':'heb',  'no':'nor', 'uk':'ukr',
'cz':'cze', 'hi':'hin',  'fa':'per', 'ur':'urd',
'da':'dan', 'hu':'hun',  'pl':'pol', 'vi':'vie',
'nl':'dut', 'is':'ice',  'pt':'por', 'cy':'',
'en':'eng', 'id':'ind',  'ro':'rum', 'yi':''}

class SearchPage(BasePage):
    """ Page which contains results as a list of movies
    """
    def iter_subtitles(self):
        tabresults = self.parser.select(self.document.getroot(),'table#search_results')
        if len(tabresults) > 0:
            table = tabresults[0]
            # for each result line, explore the subtitle list page to iter subtitles
            for line in self.parser.select(table,'tr'):
                links = self.parser.select(line,'a')
                if len(links) > 0:
                    a = links[0]
                    url = a.attrib.get('href','')
                    if "ads.opensubtitles" not in url:
                        self.browser.location("http://www.opensubtitles.org%s"%url)
                        assert self.browser.is_on_page(SubtitlesPage) or self.browser.is_on_page(SubtitlePage)
                        # subtitles page does the job
                        for subtitle in self.browser.page.iter_subtitles():
                            yield subtitle


class SubtitlesPage(BasePage):
    """ Page which contains several subtitles for a single movie
    """
    def iter_subtitles(self):
        tabresults = self.parser.select(self.document.getroot(),'table#search_results')
        if len(tabresults) > 0:
            table = tabresults[0]
            # for each result line, get informations
            # why following line doesn't work all the time (for example 'search fr sopranos guy walks' ?
            #for line in self.parser.select(table,'tr'):
            for line in table.getiterator('tr'):
                # some tr are useless, specially ads
                if line.attrib.get('id','').startswith('name'):
                    yield self.get_subtitle_from_line(line)

    def get_subtitle_from_line(self,line):
        cells = self.parser.select(line,'td')
        if len(cells) > 0:
            links = self.parser.select(line,'a')
            a = links[0]
            urldetail = a.attrib.get('href','')
            self.browser.location("http://www.opensubtitles.org%s"%urldetail)
            assert self.browser.is_on_page(SubtitlePage)
            # subtitle page does the job
            return self.browser.page.get_subtitle()


class SubtitlePage(BasePage):
    """ Page which contains a single subtitle for a movie
    """
    def get_subtitle(self):
        desc = NotAvailable
        father = self.parser.select(self.document.getroot(),'a#app_link',1).getparent()
        a = self.parser.select(father,'a')[1]
        id = a.attrib.get('href','').split('/')[-1]
        url = "http://www.opensubtitles.org/subtitleserve/sub/%s"%id
        link = self.parser.select(self.document.getroot(),'link[rel=bookmark]',1)
        title = link.attrib.get('title','')
        nb_cd = int(title.lower().split('cd')[0].split()[-1])
        lang = title.split('(')[1].split(')')[0]
        file_names = self.parser.select(self.document.getroot(),"img[title~=filename]")
        if len(file_names) > 0:
            file_name = file_names[0].getparent().text_content()
            file_name = " ".join(file_name.split())
            desc = u"files :"
            for f in file_names:
                desc_line = f.getparent().text_content()
                desc += "\n"+" ".join(desc_line.split())
        name = "%s (%s)"%(title,file_name)

        subtitle = Subtitle(id,name)
        subtitle.url = url
        for lshort,llong in LANGUAGE_CONV.items():
            if lang == llong:
                lang = lshort
                break
        subtitle.language = lang
        subtitle.nb_cd = nb_cd
        subtitle.description = desc
        return subtitle

    def iter_subtitles(self):
        yield self.get_subtitle()

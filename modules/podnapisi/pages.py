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
from weboob.capabilities.base import NotAvailable, NotLoaded
from weboob.deprecated.browser import Page


LANGUAGE_NUMBERS = {
    'sq': '29',
    'de': '5',
    'en': '2',
    'ar': '12',
    'bn': '59',
    'be': '50',
    'bg': '33',
    'ca': '53',
    'zh': '17',
    'ko': '4',
    'hr': '38',
    'da': '24',
    'es': '28',
    'et': '20',
    'fi': '31',
    'fr': '8',
    'gr': '16',
    'hi': '42',
    'nl': '23',
    'hu': '15',
    'iw': '22',
    'id': '54',
    'ga': '49',
    'is': '6',
    'it': '9',
    'ja': '11',
    'lv': '21',
    'lt': '19',
    'mk': '35',
    'ms': '55',
    'no': '3',
    'pl': '26',
    'pt': '32',
    'ro': '13',
    'ru': '27',
    'sr': '36',
    'sk': '37',
    'sl': '1',
    'sv': '25',
    'cz': '7',
    'th': '44',
    'tr': '30',
    'uk': '46',
    'vi': '51'
}


class SearchPage(Page):
    """ Page which contains results as a list of movies
    """

    def iter_subtitles(self, language):
        linksresults = self.parser.select(self.document.getroot(), 'a.subtitle_page_link')
        for link in linksresults:
            id = unicode(link.attrib.get('href', '').split('-p')[-1])
            name = unicode(link.text_content())
            tr = link.getparent().getparent().getparent()
            cdtd = self.parser.select(tr, 'td')[4]
            nb_cd = int(cdtd.text)
            description = NotLoaded
            subtitle = Subtitle(id, name)
            subtitle.nb_cd = nb_cd
            subtitle.language = language
            subtitle.description = description
            yield subtitle


class SubtitlePage(Page):
    """ Page which contains a single subtitle for a movie
    """

    def get_subtitle(self, id):
        language = NotAvailable
        url = NotAvailable
        nb_cd = NotAvailable
        links_info = self.parser.select(self.document.getroot(), 'fieldset.information a')
        for link in links_info:
            href = link.attrib.get('href', '')
            if '/fr/ppodnapisi/kategorija/jezik/' in href:
                nlang = href.split('/')[-1]
                for lang, langnum in LANGUAGE_NUMBERS.items():
                    if str(langnum) == str(nlang):
                        language = unicode(lang)
                        break

        desc = u''
        infos = self.parser.select(self.document.getroot(), 'fieldset.information')
        for info in infos:
            for p in self.parser.select(info, 'p'):
                desc += '%s\n' % (u' '.join(p.text_content().strip().split()))
            spans = self.parser.select(info, 'span')
            for span in spans:
                if span.text is not None and 'CD' in span.text:
                    nb_cd = int(self.parser.select(span.getparent(), 'span')[1].text)

        title = unicode(self.parser.select(self.document.getroot(), 'head title', 1).text)
        name = title.split(' - ')[0]

        dllinks = self.parser.select(self.document.getroot(), 'div.footer > a.download')
        for link in dllinks:
            href = link.attrib.get('href', '')
            if id in href:
                url = u'http://www.podnapisi.net%s' % href

        subtitle = Subtitle(id, name)
        subtitle.url = url
        subtitle.language = language
        subtitle.nb_cd = nb_cd
        subtitle.description = desc
        return subtitle

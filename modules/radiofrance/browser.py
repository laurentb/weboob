# * -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Johann Broudin, Laurent Bachelier
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

from weboob.tools.browser import BaseBrowser, BasePage, BrokenPageError

from StringIO import StringIO
from time import time

try:
    import json
except ImportError:
    import simplejson as json


__all__ = ['RadioFranceBrowser']


class DataPage(BasePage):
    def get_title(self):
        for metas in self.parser.select(self.document.getroot(), 'div.metas'):
            title = unicode(metas.text_content()).strip()
            if len(title):
                return title


class RssPage(BasePage):
    def get_title(self):
        titles = []
        for heading in self.parser.select(self.document.getroot(), 'h1, h2, h3, h4'):
            # Remove newlines/multiple spaces
            words = heading.text_content()
            if words:
                for word in unicode(words).split():
                    titles.append(word)
        if len(titles):
            return ' '.join(titles)


class RssAntennaPage(BasePage):
    ENCODING = 'ISO-8859-1'
    def get_track(self):
        # This information is not always available
        try:
            marquee = self.parser.select(self.document.getroot(), 'marquee', 1)
            track = self.parser.select(marquee, 'font b', 2)
            artist = unicode(track[0].text).strip() or None
            title = unicode(track[1].text).strip() or None
            return (artist, title)
        except BrokenPageError:
            return (None, None)


class RadioFranceBrowser(BaseBrowser):
    DOMAIN = None
    ENCODING = 'UTF-8'
    PAGES = {r'/playerjs/direct/donneesassociees/html\?guid=$': DataPage,
        r'http://players.tv-radio.com/radiofrance/metadatas/([a-z]+)RSS.html': RssPage,
        r'http://players.tv-radio.com/radiofrance/metadatas/([a-z]+)RSS_a_lantenne.html': RssAntennaPage}

    def get_current_playerjs(self, _id):
        self.location('http://www.%s.fr/playerjs/direct/donneesassociees/html?guid=' % _id)
        assert self.is_on_page(DataPage)

        return self.page.get_title()

    def get_current_rss(self, _id):
        self.location('http://players.tv-radio.com/radiofrance/metadatas/%sRSS.html' % _id)
        assert self.is_on_page(RssPage)

        return self.page.get_title()

    def get_current_direct(self, _id):
        json_data = self.openurl('http://www.%s.fr/sites/default/files/direct.json?_=%s' % (_id, int(time())))
        data = json.load(json_data)

        document = self.parser.parse(StringIO(data.get('html')))
        artist = document.findtext('//span[@class="artiste"]')
        title = document.findtext('//span[@class="titre"]')
        artist = unicode(artist) if artist else None
        title = unicode(title) if title else None
        return (artist, title)

    def get_current_antenna(self, _id):
        self.ENCODING = RssAntennaPage.ENCODING
        self.location('http://players.tv-radio.com/radiofrance/metadatas/%sRSS_a_lantenne.html' % _id)
        assert self.is_on_page(RssAntennaPage)
        result = self.page.get_track()
        self.ENCODING = RadioFranceBrowser.ENCODING
        return result

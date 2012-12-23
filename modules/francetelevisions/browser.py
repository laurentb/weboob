# -*- coding: utf-8 -*-

# Copyright(C) 2011-2012  Romain Bignon, Laurent Bachelier
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

import datetime

from lxml import etree

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url

from .pages import IndexPage, VideoPage
from .video import PluzzVideo


__all__ = ['PluzzBrowser']


class PluzzBrowser(BaseBrowser):
    DOMAIN = 'pluzz.francetv.fr'
    PAGES = {r'http://[w\.]*pluzz.francetv.fr/replay/1': IndexPage,
             r'http://[w\.]*pluzz.francetv.fr/recherche.*': IndexPage,
             r'http://[w\.]*pluzz.francetv.fr/videos/(.+).html': VideoPage,
            }

    @id2url(PluzzVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage)

        _id = self.page.get_id()
        if video is None:
            video = PluzzVideo(_id)

        infourl = self.page.get_info_url()
        if infourl is not None:
            self.parse_info(self.openurl(infourl).read(), video)

        return video

    def home(self):
        self.search_videos('')

    def search_videos(self, pattern):
        self.location(self.buildurl('/recherche', recherche=pattern.encode('utf-8')))

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def latest_videos(self):
        self.home()

        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def parse_info(self, data, video):
        parser = etree.XMLParser(encoding='utf-8')
        root = etree.XML(data, parser)
        assert root.tag == 'oeuvre'

        video.title = unicode(root.findtext('titre'))

        hours, minutes, seconds = root.findtext('duree').split(':')
        video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

        for vid in root.find('videos'):
            if vid.findtext('statut') == 'ONLINE' and vid.findtext('format') == 'wmv':
                video.url = unicode(vid.findtext('url'))

        date = root.findtext('diffusions/diffusion')
        if date:
            video.date = datetime.datetime.strptime(date, '%d/%m/%Y %H:%M')

        video.description = unicode(root.findtext('synopsis'))

        return video

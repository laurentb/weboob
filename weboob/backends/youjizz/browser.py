# -*- coding: utf-8 -*-

# Copyright(C) 2010  Roger Philibert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import re
import urllib
from logging import warning

from weboob.tools.browser import BaseBrowser, BrowserUnavailable
from weboob.tools.browser.decorators import check_domain, id2url
from weboob.tools.misc import iter_fields

from .pages.index import IndexPage
from .video import YoujizzVideo


__all__ = ['YoujizzBrowser']


class YoujizzBrowser(BaseBrowser):
    DOMAIN = 'youjizz.com'
    PROTOCOL = 'http'
    PAGES = {r'http://.*youjizz\.com/?': IndexPage,
             r'http://.*youjizz\.com/index.php': IndexPage,
             r'http://.*youjizz\.com/search/.+\.html': IndexPage,
            }

    @id2url(YoujizzVideo.id2url)
    def get_video(self, url, video=None):
        if video is None:
            video = YoujizzVideo()
        try:
            data = self.openurl(url).read()
        except BrowserUnavailable:
            return None
        def _get_url():
            video_file_urls = re.findall(r'"(http://media[^ ,]+\.flv)"', data)
            if len(video_file_urls) == 0:
                return None
            else:
                if len(video_file_urls) > 1:
                    warning('Many video file URL found for given URL: %s' % video_file_urls)
                return video_file_urls[0]
        m = re.search(r'http://.*youjizz\.com/videos/(.+)\.html', url)
        _id = unicode(m.group(1)) if m else None
        m = re.search(r'<title>(.+)</title>', data)
        title = unicode(m.group(1)) if m else None
        m = re.search(r'<strong>.*Runtime.*</strong>(.+)<br.*>', data)
        if m:
            minutes, seconds = (int(v) for v in unicode(m.group(1).strip()).split(':'))
            duration = minutes * 60 + seconds
        else:
            duration = 0
        video._id = _id
        video.title = title
        video.url = _get_url()
        video.duration = duration
        return video

    @check_domain
    def iter_page_urls(self, mozaic_url):
        raise NotImplementedError()

    def iter_search_results(self, pattern, required_fields=None):
        if not pattern:
            self.home()
        else:
            self.location('/search/%s-1.html' % (urllib.quote_plus(pattern)))
        assert self.is_on_page(IndexPage)

        for video in self.page.iter_videos():
            if required_fields is not None:
                required_fields_missing = set(required_fields) - set(iter_fields(video))
                if required_fields_missing:
                    self.get_video(video.id, video=video)
            yield video

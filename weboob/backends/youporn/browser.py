# -*- coding: utf-8 -*-

# Copyright(C) 2010  Romain Bignon
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


import logging

from weboob.tools.browser import BaseBrowser
from weboob.tools.browser.decorators import id2url
from weboob.tools.misc import iter_fields

from .pages.index import IndexPage
from .pages.video import VideoPage
from .video import YoupornVideo


__all__ = ['YoupornBrowser']


class YoupornBrowser(BaseBrowser):
    DOMAIN = 'youporn.com'
    PROTOCOL = 'http'
    PAGES = {'http://[w\.]*youporn\.com/?': IndexPage,
             'http://[w\.]*youporn\.com/search.*': IndexPage,
             'http://[w\.]*youporn\.com/watch/.+': VideoPage,
             'http://[w\.]*youporngay\.com:80/watch/.+': VideoPage,
            }

    @id2url(YoupornVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        if video is None:
            return video.page.video
        else:
            for k, v in iter_fields(self.page.video):
                if v and getattr(video, k) != v:
                    setattr(video, k, v)
            return video

    def iter_search_results(self, pattern, sortby, required_fields=None):
        if not pattern:
            self.home()
        else:
            self.location(self.buildurl('/search/%s' % sortby, query=pattern))
        assert self.is_on_page(IndexPage)
        for video in self.page.iter_videos():
            if required_fields is not None:
                missing_required_fields = set(required_fields) - set(k for k, v in iter_fields(video) if v)
                if missing_required_fields:
                    logging.debug(u'Completing missing required fields: %s' % missing_required_fields)
                    self.get_video(video.id, video=video)
                    missing_required_fields = set(required_fields) - set(k for k, v in iter_fields(video) if v)
                    if missing_required_fields:
                        raise Exception(u'Could not load all required fields. Missing: %s' % missing_required_fields)
            yield video

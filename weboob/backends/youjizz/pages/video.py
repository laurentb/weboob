# -*- coding: utf-8 -*-

"""
Copyright(C) 2010  Roger Philibert

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""

from logging import error, warning
import re

from weboob.capabilities.video import Video
from weboob.tools.browser import BasePage

class VideoPage(BasePage):
    URL_REGEX = re.compile(r'http://.*youjizz\.com/videos/.+-(\d+)\.html')
    VIDEO_FILE_REGEX = re.compile(r'"(http://media[^ ,]+\.flv)"')

    def on_loaded(self):
        details = self.get_details()
        self.video = Video(_id=self.get_id(), title=details.get('title', u''), url=self.get_url(),
                duration=details.get('duration', 0), nsfw=True)

    def get_id(self):
        m = self.URL_REGEX.match(self.url)
        if m:
            return int(m.group(1))
        warning("Unable to parse ID")
        return 0

    def get_url(self):
        video_file_urls = re.findall(self.VIDEO_FILE_REGEX, self.browser.parser.tostring(self.document))
        if len(video_file_urls) == 0:
            return None
        else:
            if len(video_file_urls) > 1:
                error('Many video file URL found for given URL: %s' % video_file_urls)
            return video_file_urls[0]

    def get_details(self):
        results = {}
        div = self.document.getroot().cssselect('#video_text')[0]
        results['title'] = unicode(div.find('h2').text).strip()
        minutes, seconds = [int(v) for v in [e for e in div.cssselect('strong') if e.text.startswith('Runtime')][0].tail.split(':')]
        print minutes, seconds
        results['duration'] = minutes * 60 + seconds
        return results

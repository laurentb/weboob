# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Romain Bignon
# Copyright(C) 2012 François Revol
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

from weboob.tools.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError

from weboob.tools.browser import BasePage
from weboob.tools.json import json

import re
import datetime
from dateutil.parser import parse as parse_dt

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import BaseImage
from weboob.tools.browser import BrokenPageError

from .video import VimeoVideo


__all__ = ['VideoPage']


class VideoPage(BasePage):
    def get_video(self, video=None):
        if video is None:
            video = VimeoVideo(self.group_dict['id'])
        self.set_details(video)

        video.set_empty_fields(NotAvailable)
        return video

    def set_details(self, v):
        # try to get as much from the page itself
        obj = self.parser.select(self.document.getroot(), 'h1[itemprop=name]')
        if len(obj) > 0:
            v.title = unicode(obj[0].text)

        obj = self.parser.select(self.document.getroot(), 'meta[itemprop=dateCreated]')
        if len(obj) > 0:
            v.date = parse_dt(obj[0].attrib['content'])

        #obj = self.parser.select(self.document.getroot(), 'meta[itemprop=duration]')

        obj = self.parser.select(self.document.getroot(), 'meta[itemprop=thumbnailUrl]')
        if len(obj) > 0:
            v.thumbnail = BaseImage(obj[0].attrib['content'])
            v.thumbnail.url = v.thumbnail.id

        data = None

        # First try to find the JSON data in the page itself.
        # it's the only location in case the video is not allowed to be embeded
        for script in self.parser.select(self.document.getroot(), 'script'):
            m = re.match('.* = {config:({.*}),assets:.*', unicode(script.text), re.DOTALL)
            if m:
                data = json.loads(m.group(1))
                break

        # Else fall back to the API
        if data is None:
            # for the rest, use the JSON config descriptor
            json_data = self.browser.openurl('http://%s/video/%s/config?type=%s&referrer=%s' % ("player.vimeo.com", int(v.id), "html5_desktop_local", ""))
            data = json.load(json_data)

        if data is None:
            raise BrokenPageError('Unable to get JSON config for id: %r' % int(v.id))

        if v.title is None:
            v.title = unicode(data['video']['title'])
        if v.thumbnail is None:
            v.thumbnail = BaseImage(data['video']['thumbnail'])
            v.thumbnail.url = v.thumbnail.id
        v.author = data['video']['owner']['name']
        v.duration = datetime.timedelta(seconds=int(data['video']['duration']))

        # determine available codec and quality
        # use highest quality possible
        quality = 'sd'
        codec = None
        if 'vp6' in data['request']['files']:
            codec = 'vp6'
        if 'vp8' in data['request']['files']:
            codec = 'vp8'
        if 'h264' in data['request']['files']:
            codec = 'h264'
        if not codec:
            raise BrokenPageError('Unable to detect available codec for id: %r' % int(v.id))

        if 'hd' in data['request']['files'][codec]:
            quality = 'hd'

        v.url = data['request']['files'][codec][quality]['url']
        return v

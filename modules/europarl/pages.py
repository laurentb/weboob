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

from weboob.deprecated.mech import ClientForm
ControlNotFoundError = ClientForm.ControlNotFoundError

from weboob.deprecated.browser import Page

import re
import datetime

from weboob.capabilities.base import NotAvailable
from weboob.deprecated.browser import BrokenPageError

from .video import EuroparlVideo


class VideoPage(Page):
    def get_video(self, video=None):
        if video is None:
            video = EuroparlVideo(self.group_dict['id'])
        video.title = unicode(self.get_title())
        video.url = unicode(self.get_url())
        self.set_details(video)

        video.set_empty_fields(NotAvailable)
        return video

    def get_url(self):
        # search for <input id="codeUrl">
        # TODO: plenaries can be downloaded as mp4...
        obj = self.parser.select(self.document.getroot(), 'input#codeUrl', 1)
        if obj is None:
            return None
        return obj.attrib['value']

    def get_title(self):
        obj = self.parser.select(self.document.getroot(), 'h1#player_subjectTitle')
        if len(obj) < 1:
            obj = self.parser.select(self.document.getroot(), 'title')
            if len(obj) < 1:
                return None
        title = obj[0].text.strip()
        obj = self.parser.select(self.document.getroot(), 'span.ep_subtitle')
        if len(obj) < 1:
            return title

        for span in self.parser.select(obj[0], 'span.ep_acronym, span.ep_theme'):
            if span.text_content():
                title += ' ' + span.text_content().strip()

        return title

    def set_details(self, v):
        v.author = u'European Parliament'
        obj = self.parser.select(self.document.getroot(), 'meta[name=available]', 1)
        if obj is not None:
            value = obj.attrib['content']
            m = re.match('(\d\d)-(\d\d)-(\d\d\d\d)\s*(\d\d):(\d\d)', value)
            if not m:
                raise BrokenPageError('Unable to parse datetime: %r' % value)
            day = m.group(1)
            month = m.group(2)
            year = m.group(3)
            hour = m.group(4)
            minute = m.group(5)
            v.date = datetime.datetime(year=int(year),
                                       month=int(month),
                                       day=int(day),
                                       hour=int(hour),
                                       minute=int(minute))

        obj = self.parser.select(self.document.getroot(), 'span.ep_subtitle', 1)
        if obj is not None:
            span = self.parser.select(obj, 'span.ep_date', 1)
            value = span.text
            m = re.match('(\d\d):(\d\d)\s*\/\s*(\d\d):(\d\d)\s*-\s*(\d\d)-(\d\d)-(\d\d\d\d)', value)
            if not m:
                raise BrokenPageError('Unable to parse datetime: %r' % value)
            bhour = m.group(1)
            bminute = m.group(2)
            ehour = m.group(3)
            eminute = m.group(4)
            day = m.group(5)
            month = m.group(6)
            year = m.group(7)

            start = datetime.datetime(year=int(year),
                                      month=int(month),
                                      day=int(day),
                                      hour=int(bhour),
                                      minute=int(bminute))
            end = datetime.datetime(year=int(year),
                                    month=int(month),
                                    day=int(day),
                                    hour=int(ehour),
                                    minute=int(eminute))

            v.duration = end - start

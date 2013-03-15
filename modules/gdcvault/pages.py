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

import re
import datetime
from dateutil.parser import parse as parse_dt

from weboob.capabilities.base import NotAvailable
from weboob.tools.browser import BrokenPageError

from .video import GDCVaultVideo

#import lxml.etree


__all__ = ['VideoPage']


class VideoPage(BasePage):
    def get_video(self, video=None):
        if video is None:
            video = GDCVaultVideo(self.group_dict['id'])

        # the config file has it too, but in CDATA
        obj = self.parser.select(self.document.getroot(), 'title')
        if len(obj) > 0:
            title = obj[0].text.strip()
            m = re.match('GDC Vault\s+-\s+(.*)', title)
            if m:
                title = m.group(1)
        video.title = unicode(title)

        # get the config file for the rest
        obj = self.parser.select(self.document.getroot(), 'iframe', 1)
        if obj is None:
            return None
        iframe_url = obj.attrib['src']
        m = re.match('(http:.*)player.html\?.*xmlURL=([^&]+)\&token=([^&]+)', iframe_url)
        if not m:
            return None
        config_url = m.group(1) + m.group(2)

        #config = self.browser.openurl(config_url).read()
        config = self.browser.get_document(self.browser.openurl(config_url))

        obj = self.parser.select(config.getroot(), 'akamaihost', 1)
        host = obj.text
        if host is None:
            raise BrokenPageError('Missing tag in xml config file')

        videos = {}

        obj = self.parser.select(config.getroot(), 'speakervideo', 1)
        videos['speaker'] = 'rtmp://' + host + '/' + obj.text

        obj = self.parser.select(config.getroot(), 'slidevideo', 1)
        videos['slides'] = 'rtmp://' + host + '/' + obj.text

        #print videos

        obj = self.parser.select(config.getroot(), 'date', 1)
        video.date = parse_dt(obj.text)

        obj = self.parser.select(config.getroot(), 'duration', 1)
        m = re.match('(\d\d):(\d\d):(\d\d)', obj.text)
        if m:
            video.duration = datetime.timedelta(hours = int(m.group(1)),
                                                minutes = int(m.group(2)),
                                                seconds = int(m.group(3)))

        obj = self.parser.select(config.getroot(), 'speaker', 1)
        #print obj.text_content()

        #TODO: speaker as CDATA
        #video.author = u'European Parliament'

        #XXX
        video.url = unicode(videos['speaker'])
        #self.set_details(video)

        video.set_empty_fields(NotAvailable)
        return video

        obj = self.parser.select(self.document.getroot(), 'title')
        if len(obj) < 1:
            return None
        title = obj[0].text.strip()
        m = re.match('GDC Vault\s+-\s+(.*)', title)
        if m:
            title = m.group(1)

    def set_details(self, v):
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

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


from weboob.deprecated.browser import Page
from weboob.tools.compat import quote

import re
import datetime
from dateutil.parser import parse as parse_dt

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail
from weboob.deprecated.browser import BrokenPageError

#HACK
from urllib2 import HTTPError

from .video import GDCVaultVideo

#import lxml.etree

# TODO: check title on 1439


class IndexPage(Page):
    def iter_videos(self):
        for a in self.parser.select(self.document.getroot(), 'section.conference ul.media_items li.featured a.session_item'):
            href = a.attrib.get('href', '')
            # print href
            m = re.match('/play/(\d+)/.*', href)
            if not m:
                continue
            # print m.group(1)
            video = GDCVaultVideo(m.group(1))

            # get title
            try:
                video.title = unicode(self.parser.select(a, 'div.conference_info p strong', 1).text)
            except IndexError:
                video.title = NotAvailable

            # get description
            try:
                video.description = unicode(self.parser.select(a, 'div.conference_info p', 1).text)
            except IndexError:
                video.description = NotAvailable

            # get thumbnail
            img = self.parser.select(a, 'div.featured_image img', 1)
            if img is not None:
                video.thumbnail = Thumbnail(img.attrib['src'])
                video.thumbnail.url = video.thumbnail.id
            else:
                video.thumbnail = NotAvailable

            #m = re.match('id-(\d+)', a.attrib.get('class', ''))
            #if not m:
            #    continue
            # FIXME
            yield video

# the search page class uses a JSON parser,
# since it's what search.php returns when POSTed (from Ajax)


class SearchPage(Page):
    def iter_videos(self):
        if self.document is None or self.document['data'] is None:
            raise BrokenPageError('Unable to find JSON data')
        for data in self.document['data']:
            video = GDCVaultVideo.get_video_from_json(data)
            # TODO: split type 4 videos into id and id#slides
            if video is None:
                continue
            yield video


class VideoPage(Page):
    def get_video(self, video=None):
        # check for slides id variant
        want_slides = False
        m = re.match('.*#slides', self.url)
        if m:
            want_slides = True
            # not sure it's safe
            self.group_dict['id'] += '#slides'

        if video is None:
            video = GDCVaultVideo(self.group_dict['id'])

        # the config file has it too, but in CDATA and only for type 4
        obj = self.parser.select(self.document.getroot(), 'title')
        title = None
        if len(obj) > 0:
            try:
                title = unicode(obj[0].text)
            except UnicodeDecodeError as e:
                title = None

        if title is None:
            obj = self.parser.select(self.document.getroot(), 'meta[name=title]')
            if len(obj) > 0:
                if 'content' in obj[0].attrib:
                    try:
                        # FIXME: 1013483 has buggus title (latin1)
                        # for now we just pass it as-is
                        title = obj[0].attrib['content']
                    except UnicodeDecodeError as e:
                        # XXX: this doesn't even works!?
                        title = obj[0].attrib['content'].decode('iso-5589-15')

        if title is not None:
            title = title.strip()
            m = re.match('GDC Vault\s+-\s+(.*)', title)
            if m:
                title = m.group(1)
            video.title = title

        #TODO: POST back the title to /search.php and filter == id to get
        # cleaner (JSON) data... (though it'd be much slower)

        # try to find an iframe (type 3 and 4)
        obj = self.parser.select(self.document.getroot(), 'iframe')
        if len(obj) == 0:
            # type 1 or 2 (swf+js)
            # find which script element contains the swf args
            for script in self.parser.select(self.document.getroot(), 'script'):
                m = re.match(".*new SWFObject.*addVariable\('type', '(.*)'\).*", unicode(script.text), re.DOTALL)
                if m:
                    video.ext = m.group(1)

                m = re.match(".*new SWFObject.*addVariable\(\"file\", encodeURIComponent\(\"(.*)\"\)\).*", unicode(script.text), re.DOTALL)
                if m:
                    video.url = "http://gdcvault.com%s" % (m.group(1))
                    # TODO: for non-free (like 769),
                    # must be logged to use /mediaProxy.php

                    # FIXME: doesn't seem to work yet, we get 2 bytes as html
                    # 769 should give:
                    # http://twvideo01.ubm-us.net/o1/gdcradio-net/2007/gdc/GDC07-4889.mp3
                    # HACK: we use mechanize directly here for now... FIXME
                    #print "asking for redirect on '%s'" % (video.url)
                    #self.browser.addheaders += [['Referer', 'http://gdcvault.com/play/%s' % self.group_dict['id']]]
                    #print self.browser.addheaders
                    self.browser.set_handle_redirect(False)
                    try:
                        self.browser.open_novisit(video.url)
                        # headers = req.info()
                        # if headers.get('Content-Type', '') == 'text/html' and headers.get('Content-Length', '') == '2':
                        # print 'BUG'

                        #print req.code
                    except HTTPError as e:
                        #print e.getcode()
                        if e.getcode() == 302 and hasattr(e, 'hdrs'):
                            #print e.hdrs['Location']
                            video.url = unicode(e.hdrs['Location'])
                    self.browser.set_handle_redirect(True)

                    video.set_empty_fields(NotAvailable)
                    return video

            #XXX: raise error?
            return None

        obj = obj[0]
        if obj is None:
            return None
        # type 3 or 4 (iframe)
        # get the config file for the rest
        iframe_url = obj.attrib['src']

        # 1015020 has a boggus url
        m = re.match('http:/event(.+)', iframe_url)
        if m:
            iframe_url = 'http://event' + m.group(1)

        # print iframe_url
        # 1013798 has player169.html
        # 1012186 has player16x9.html
        # some other have /somethingplayer.html...
        # 1441 has a space in the xml filename, which we must not strip
        m = re.match('(http:.*/)[^/]*player[0-9a-z]*\.html\?.*xmlURL=([^&]+\.xml).*\&token=([^& ]+)', iframe_url)

        if not m:
            m = re.match('/play/mediaProxy\.php\?sid=(\d+)', iframe_url)
            if m is None:
                return None
            # TODO: must be logged to use /mediaProxy.php
            # type 3 (pdf slides)
            video.ext = u'pdf'
            video.url = "http://gdcvault.com%s" % (unicode(iframe_url))

            # HACK: we use mechanize directly here for now... FIXME
            # print "asking for redirect on '%s'" % (video.url)
            self.browser.set_handle_redirect(False)
            try:
                self.browser.open_novisit(video.url)
            except HTTPError as e:
                if e.getcode() == 302 and hasattr(e, 'hdrs'):
                    video.url = unicode(e.hdrs['Location'])
            self.browser.set_handle_redirect(True)

            video.set_empty_fields(NotAvailable)
            return video

        # type 4 (dual screen video)

        # token doesn't actually seem required
        # 1441 has a space in the xml filename
        xml_filename = quote(m.group(2))
        config_url = m.group(1) + xml_filename + '?token=' + m.group(3)

        # self.browser.addheaders += [['Referer', 'http://gdcvault.com/play/%s' % self.group_dict['id']]]
        # print self.browser.addheaders
        # TODO: fix for 1015021 & others (forbidden)
        #config = self.browser.openurl(config_url).read()
        config = self.browser.get_document(self.browser.openurl(config_url))

        obj = self.parser.select(config.getroot(), 'akamaihost', 1)
        host = obj.text
        if host is None:
            raise BrokenPageError('Missing tag in xml config file')

        if host == "smil":
            # the rtmp URL is described in a smil file,
            # with several available bitrates
            obj = self.parser.select(config.getroot(), 'speakervideo', 1)
            smil = self.browser.get_document(self.browser.openurl(obj.text))
            obj = self.parser.select(smil.getroot(), 'meta', 1)
            # TODO: error checking
            base = obj.attrib.get('base', '')
            best_bitrate = 0
            path = None
            obj = self.parser.select(smil.getroot(), 'video')
            # choose the best bitrate
            for o in obj:
                rate = int(o.attrib.get('system-bitrate', 0))
                if rate > best_bitrate:
                    path = o.attrib.get('src', '')
            video.url = unicode(base + '/' + path)

        else:
            # not smil, the rtmp url is directly here as host + path
            # for id 1373 host is missing '/ondemand'
            # only add it when only a domain is specified without path
            m = re.match('^[^\/]+$', host)
            if m:
                host += "/ondemand"

            videos = {}

            obj = self.parser.select(config.getroot(), 'speakervideo', 1)
            if obj.text is not None:
                videos['speaker'] = 'rtmp://' + host + '/' + quote(obj.text)

            obj = self.parser.select(config.getroot(), 'slidevideo', 1)
            if obj.text is not None:
                videos['slides'] = 'rtmp://' + host + '/' + quote(obj.text)

            # print videos
            # XXX
            if 'speaker' in videos:
                video.url = unicode(videos['speaker'])
            elif 'slides' in videos:
                # 1016627 only has slides, so fallback to them
                video.url = unicode(videos['slides'])

            if want_slides:
                if 'slides' in videos:
                    video.url = unicode(videos['slides'])
            # if video.url is none: raise ? XXX

        obj = self.parser.select(config.getroot(), 'date', 1)
        if obj.text is not None:
            # 1016634 has "Invalid Date"
            try:
                video.date = parse_dt(obj.text)
            except ValueError as e:
                video.date = NotAvailable

        obj = self.parser.select(config.getroot(), 'duration', 1)
        m = re.match('(\d\d):(\d\d):(\d\d)', obj.text)
        if m:
            video.duration = datetime.timedelta(hours = int(m.group(1)),
                                                minutes = int(m.group(2)),
                                                seconds = int(m.group(3)))

        obj = self.parser.select(config.getroot(), 'speaker', 1)
        #print obj.text_content()

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

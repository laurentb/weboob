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

#HACK
from urllib2 import HTTPError

from weboob.tools.browser import BasePage
from weboob.tools.browser import BrowserRetry
from weboob.tools.json import json

from StringIO import StringIO
import re
import datetime
from dateutil.parser import parse as parse_dt

from weboob.tools.capabilities.thumbnail import Thumbnail
from weboob.capabilities.base import NotAvailable
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
            v.thumbnail = Thumbnail(unicode(obj[0].attrib['content']))

        # for the rest, use the JSON config descriptor
        json_data = self.browser.openurl('http://%s/config/%s?type=%s&referrer=%s' % ("player.vimeo.com", int(v.id), "html5_desktop_local", ""))
        data = json.load(json_data)
        if data is None:
            raise BrokenPageError('Unable to get JSON config for id: %r' % v.id)
        #print data

        if v.title is None:
            v.title = unicode(data['video']['title'])
        if v.thumbnail is None:
            v.thumbnail = Thumbnail(unicode(data['video']['thumbnail']))
        v.duration = datetime.timedelta(seconds=int(data['video']['duration']))

        # log ourself to the site to validate the signature
        log_data = self.browser.openurl('http://%s/log/client' % ("player.vimeo.com"), 'request_signature=%s&video=true&h264=probably&vp8=probably&vp6=probably&flash=null&touch=false&screen_width=1920&screen_height=1080' % (data['request']['signature']))
        
        # failed attempts ahead

        # try to get the filename and url from the SMIL descriptor
        # smil_url = data['video']['smil']['url']
        # smil_url += "?sig=%s&time=%s" % (data['request']['signature'], data['request']['timestamp'])
        # smil = self.browser.get_document(self.browser.openurl(smil_url))

        # obj = self.parser.select(smil.getroot(), 'meta[name=httpBase]', 1)
        # http_base = obj.attrib['content']
        # print http_base
        # if http_base is None:
        #     raise BrokenPageError('Missing tag in smil file')

        # url = None
        # br = 0
        # for obj in self.parser.select(smil.getroot(), 'video'):
        #     print 'BR:' + obj.attrib['system-bitrate'] + ' url: ' + obj.attrib['src']

        #     if int(obj.attrib['system-bitrate']) > br :
        #         url = obj.attrib['src']

        # rtmp_base = 'rtmp://' + data['request']['cdn_url'] + '/'

        # not working yet...

        #url += "&time=%s&sig=%s" % (data['request']['timestamp'], data['request']['signature'])
        #url = "%s/%s/%s" %(data['request']['timestamp'], data['request']['signature'], url)
        #v.url = unicode(http_base + url)
        #v.url = unicode("http://" + data['request']['cdn_url'] + "/" + url)
        #v.url = unicode(rtmp_base + url)

        # TODO: determine quality from data[...]['files']['h264']
        v.url = unicode("http://player.vimeo.com/play_redirect?quality=sd&codecs=h264&clip_id=%d&time=%s&sig=%s&type=html5_desktop_local" % (int(v.id), data['request']['timestamp'] , data['request']['signature']))

        # attempt to determine the redirected URL to pass it instead
        # since the target server doesn't check for User-Agent, unlike
        # for the source one.
        # HACK: we use mechanize directly here for now... FIXME
        self.browser.set_handle_redirect(False)
        #@retry(BrowserHTTPError, tries=0)
        #redir = self.browser.openurl(v.url, if_fail = 'raise')
        try:
            redir = self.browser.open_novisit(v.url)
        except HTTPError, e:
            if e.getcode() == 302 and hasattr(e, 'hdrs'):
                #print e.hdrs['Location']
                v.url = unicode(e.hdrs['Location'])

        self.browser.set_handle_redirect(True)
        

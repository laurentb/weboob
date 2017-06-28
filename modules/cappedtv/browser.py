# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lord
#
# This module is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.

from collections import OrderedDict
import datetime

from weboob.capabilities.base import NotAvailable
from weboob.tools.misc import to_unicode
from weboob.deprecated.browser import Page
from weboob.deprecated.browser import BrokenPageError
from weboob.deprecated.browser import Browser
from weboob.deprecated.browser.decorators import id2url
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo
from weboob.tools.compat import quote_plus


__all__ = ['CappedBrowser']


class CappedVideo(BaseVideo):
    def __init__(self, *args, **kwargs):
        BaseVideo.__init__(self, *args, **kwargs)
        self.nsfw = False
        self.ext = u'mp4'

    @classmethod
    def id2url(cls, _id):
        return 'http://capped.tv/%s' % _id


# parser for search pages
class IndexPage(Page):
    def iter_videos(self):
        # When no results are found, the website returns random results
        sb = self.parser.select(self.document.getroot(), 'div.search form input.searchbox', 1)
        if sb.value == 'No Results Found':
            return

        #Extracting meta data from results page
        vidbackdrop_list = self.parser.select(self.document.getroot(), 'div.vidBackdrop    ')
        for vidbackdrop in vidbackdrop_list:
            url = self.parser.select(vidbackdrop, 'a', 1).attrib['href']
            _id = url[2:]

            video = CappedVideo(_id)
            video.set_empty_fields(NotAvailable, ('url',))

            video.title = to_unicode(self.parser.select(vidbackdrop, 'div.vidTitle a', 1).text)
            video.author = to_unicode(self.parser.select(vidbackdrop, 'div.vidAuthor a', 1).text)

            thumbnail_url = 'http://cdn.capped.tv/pre/%s.png' % _id
            video.thumbnail = Thumbnail(thumbnail_url)
            video.thumbnail.url = to_unicode(video.thumbnail.id)

            #we get the description field
            duration_tmp = self.parser.select(vidbackdrop, 'div.vidInfo', 1)
            #we remove tabs and spaces
            duration_tmp2 = duration_tmp.text[7:]
            #we remove all fields exept time
            duration_tmp3 = duration_tmp2.split(' ')[0]
            #we transform it in datetime format
            parts = duration_tmp3.split(':')
            if len(parts) == 1:
                hours = minutes = 0
                seconds = parts[0]
            elif len(parts) == 2:
                hours = 0
                minutes, seconds = parts
            elif len(parts) == 3:
                hours, minutes, seconds = parts
            else:
                raise BrokenPageError('Unable to parse duration %r' % duration_tmp)

            video.duration = datetime.timedelta(hours=int(hours), minutes=int(minutes), seconds=int(seconds))

            yield video


# parser for the video page
class VideoPage(Page):
    def get_video(self, video=None):
        _id = to_unicode(self.group_dict['id'])
        if video is None:
            video = CappedVideo(_id)
            video.set_empty_fields(NotAvailable)

        title_tmp = self.parser.select(self.document.getroot(), 'title', 1)
        video.title = to_unicode(title_tmp.text.strip())

        # Videopages doesn't have duration information (only results pages)
        video.url = u'http://cdn.capped.tv/vhq/%s.mp4' % _id
        return video


class CappedBrowser(Browser):
    DOMAIN = 'capped.tv'
    PROTOCOL = 'http'
    ENCODING = None
    PAGES = OrderedDict((
            (r'http://capped\.tv/?', IndexPage),
            (r'http://capped\.tv/newest', IndexPage),
            (r'http://capped\.tv/mostviews', IndexPage),
            (r'http://capped\.tv/leastviews', IndexPage),
            (r'http://capped\.tv/monthtop', IndexPage),
            (r'http://capped\.tv/monthbottom', IndexPage),
            (r'http://capped\.tv/alpha', IndexPage),
            (r'http://capped\.tv/ahpla', IndexPage),
            (r'http://capped\.tv/search\?s\=(?P<pattern>.+)', IndexPage),
            (r'http://capped\.tv/(?P<id>.+)', VideoPage),
            ))

    @id2url(CappedVideo.id2url)
    def get_video(self, url, video=None):
        self.location(url)
        assert self.is_on_page(VideoPage), 'Should be on video page.'
        return self.page.get_video(video)

    def search_videos(self, pattern):
        self.location('/search?s=%s' % (quote_plus(pattern.encode('utf-8'))))
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

    def latest_videos(self):
        self.home()
        assert self.is_on_page(IndexPage)
        return self.page.iter_videos()

# -*- coding: utf-8 -*-

# Copyright(C) 2012 Lord
#
# This module is free software. It comes without any warranty, to
# the extent permitted by applicable law. You can redistribute it
# and/or modify it under the terms of the Do What The Fuck You Want
# To Public License, Version 2, as published by Sam Hocevar. See
# http://sam.zoy.org/wtfpl/COPYING for more details.


from weboob.capabilities.video import CapVideo, BaseVideo
from weboob.capabilities.collection import CapCollection, CollectionNotFound
from weboob.tools.backend import Module
from .browser import CappedBrowser, CappedVideo


__all__ = ['CappedModule']


class CappedModule(Module, CapVideo, CapCollection):
    NAME = 'cappedtv'
    MAINTAINER = u'Lord'
    EMAIL = 'lord@lordtoniok.com'
    VERSION = '1.4'
    DESCRIPTION = 'Capped.tv demoscene website'
    LICENSE = 'WTFPLv2'
    BROWSER = CappedBrowser

    def get_video(self, _id):
        with self.browser:
            return self.browser.get_video(_id)

    def search_videos(self, pattern, sortby=CapVideo.SEARCH_RELEVANCE, nsfw=None):
        with self.browser:
            return self.browser.search_videos(pattern)

    def fill_video(self, video, fields):
        if fields != ['thumbnail']:
            with self.browser:
                video = self.browser.get_video(CappedVideo.id2url(video.id), video)
        if 'thumbnail' in fields and video.thumbnail:
            with self.browser:
                video.thumbnail.data = self.browser.readurl(video.thumbnail.url)

        return video

    def iter_resources(self, objs, split_path):
        if BaseVideo in objs:
            collection = self.get_collection(objs, split_path)
            if collection.path_level == 0:
                yield self.get_collection(objs, [u'latest'])
            if collection.split_path == [u'latest']:
                for video in self.browser.latest_videos():
                    yield video

    def validate_collection(self, objs, collection):
        if collection.path_level == 0:
            return
        if BaseVideo in objs and collection.split_path == [u'latest']:
            collection.title = u'Latest CappedTV videos'
            return
        raise CollectionNotFound(collection.split_path)

    OBJECTS = {CappedVideo: fill_video}

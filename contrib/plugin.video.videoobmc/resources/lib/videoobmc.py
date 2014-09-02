#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import re

from datetime import timedelta, datetime
from .base.weboobmc import Weboobmc
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.image import BaseImage
from weboob.capabilities.collection import Collection


class Videoobmc(Weboobmc):
    def __init__(self, count=10, nsfw=False):
        Weboobmc.__init__(self, count=count)
        self.backends = list(self.get_loaded_backends('CapVideo'))
        _nsfw = 'on' if nsfw else 'off'
        self._call_weboob('videoob', 'nsfw', argument=_nsfw)

    def search(self, pattern, backend=''):
        #videoob search pattern -f json
        options = {'--select': 'id,title,date,description,author,duration,thumbnail,url'}
        if backend:
            options['-b'] = backend
        _videos = self._json_call_weboob('videoob', 'search', argument=pattern, options=options)
        if _videos:
            for _video in _videos:
                yield self.create_video_from_json(_video)

    def create_video_from_json(self, _video):
        video = BaseVideo()
        video.id = u'%s' % _video['id']
        video.backend = u'%s' % _video['id'].split('@')[-1]

        if 'url' in _video.keys():
            video.url = u'%s' % _video['url']

        if 'thumbnail' in _video.keys() and _video['thumbnail'] and 'url' in _video['thumbnail'].keys():
            video.thumbnail = BaseImage()
            video.thumbnail.url = u'%s' % _video['thumbnail']['url']
        else:
            video.thumbnail.url = u''
        video.title = u'%s' % _video['title']

        if _video['date']:
            _date = re.search('(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*', _video['date'])

            try:
                datetime.strptime(_date.group(1), '%Y-%m-%d %H:%M:%S')
            except TypeError:
                datetime(*(time.strptime(_date.group(1), '%Y-%m-%d %H:%M:%S')[0:6]))

        video.description = u'%s' % _video['description']
        video.author = u'%s' % _video['author']

        if _video['duration']:
            _duration = _video['duration'].split(':')
            video.duration = timedelta(hours=int(_duration[0]), minutes=int(_duration[1]), seconds=int(_duration[2]))

        return video

    def get_video(self, video, backend):
        #videoob info _id -f json
        _video = self._json_call_weboob('videoob', 'info', argument=video.id)
        if _video and len(_video) > 0:
            return self.create_video_from_json(_video[0])

    def ls(self, backend, path=''):
        options = {'-b': backend, '-n': 50}
        result = self._json_call_weboob('videoob', 'ls', options=options, argument=path)
        return self.separate_collections_and_videos(result)

    def separate_collections_and_videos(self, objs):
        videos = []
        categories = []
        for obj in objs:
            if self.is_category(obj):
                categories.append(self.create_category_from_json(obj))
            else:
                video = BaseVideo()
                video.id = obj['id'].split('@')[0]
                video.backend = obj['id'].split('@')[-1]
                videos.append(video)
        return categories, videos

    def create_category_from_json(self, obj):
        collection = Collection(obj['split_path'].split('/'))
        collection.title = obj['title']
        collection.id = obj['id'].split('@')[0]
        collection.backend = obj['id'].split('@')[1]
        return collection

    def download(self, _id, path, backend):
        #videoob download _id path
        options = {'-b': backend}
        self._call_weboob('videoob', 'download', options=options, argument=u'%s %s' % (_id, path))

# -*- coding: utf-8 -*-

# Copyright(C) 2017  Vincent A
#
# This file is part of weboob.
#
# weboob is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# weboob is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with weboob. If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess

from weboob.capabilities.base import NotAvailable
from weboob.capabilities.image import Thumbnail
from weboob.capabilities.video import BaseVideo
from weboob.tools.date import parse_date
from weboob.tools.json import json
from weboob.tools.application.media_player import MediaPlayer
from weboob.tools.compat import unicode


from datetime import timedelta

__all__ = ('video_info',)


def video_info(url):
    """Fetch info about a video using youtube-dl

    :param url: URL of the web page containing the video
    :rtype: :class:`weboob.capabilities.video.Video`
    """

    if not MediaPlayer._find_in_path(os.environ['PATH'], 'youtube-dl'):
        raise Exception('Please install youtube-dl')

    try:
        j = json.loads(subprocess.check_output(['youtube-dl', '-f', 'best', '-J', url]))
    except subprocess.CalledProcessError:
        return

    v = BaseVideo(id=url)
    v.title = unicode(j.get('title')) if j.get('title') else NotAvailable
    v.ext = unicode(j.get('ext')) if j.get('ext') else NotAvailable
    v.description = unicode(j.get('description')) if j.get('description') else NotAvailable
    v.url = unicode(j['url'])
    v.duration = timedelta(seconds=j.get('duration')) if j.get('duration') else NotAvailable
    v.author = unicode(j.get('uploader')) if j.get('uploader') else NotAvailable
    v.rating = j.get('average_rating') or NotAvailable

    if j.get('thumbnail'):
        v.thumbnail = Thumbnail(unicode(j['thumbnail']))

    d = j.get('upload_date', j.get('release_date'))
    if d:
        v.date = parse_date(d)

    return v

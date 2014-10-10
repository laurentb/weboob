# -*- coding: utf-8 -*-

# Copyright(C) 2010-2011 Roger Philibert
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


from weboob.capabilities.image import BaseImage
from weboob.capabilities.video import BaseVideo
from weboob.capabilities.base import NotAvailable

import re
from dateutil.parser import parse as parse_dt


class GDCVaultVideo(BaseVideo):
    def __init__(self, *args, **kwargs):
        BaseVideo.__init__(self, *args, **kwargs)
        # not always flv...
        self.ext = NotAvailable

    @classmethod
    def id2url(cls, _id):
        # attempt to enlarge the id namespace to differentiate
        # videos from the same page
        m = re.match('\d+#speaker', _id)
        if m:
            return u'http://www.gdcvault.com/play/%s#speaker' % _id
        m = re.match('\d+#slides', _id)
        if m:
            return u'http://www.gdcvault.com/play/%s#slides' % _id
        return u'http://www.gdcvault.com/play/%s' % _id

    @classmethod
    def get_video_from_json(self, data):
        # session_id is unique per talk
        # vault_media_id is unique per page
        # (but can refer to 2 video files for dual screen)
        # solr_id is "${vault_media_id}.${conference_id}.${session_id}.$vault_media_type_id{}"

        # XXX: do we filter them or let people know about them?
        #if 'anchor' in data:
        #    if data['anchor']['href'] == '#':
        #        # file will not be accessible (not free and not logged in)
        #        return None

        if 'vault_media_id' not in data:
            return None
        media_id = int(data['vault_media_id'])
        video = GDCVaultVideo(media_id)

        # 1013679 has \n in title...
        video.title = unicode(data.get('session_name', '').replace('\n', ''))

        # TODO: strip out <p>, <br> and other html...
        # XXX: 1013422 has all 3 and !=
        if 'overview' in data:
            video.description = unicode(data['overview'])
        elif 'spell' in data:
            video.description = unicode(data['spell'])
        else:
            video.description = unicode(data.get('description', ''))

        if 'image' in data:
            video.thumbnail = BaseImage(data['image'])
            video.thumbnail.url = video.thumbnail.id

        if 'speakers_name' in data:
            video.author = unicode(", ".join(data['speakers_name']))

        if 'start_date' in data:
            video.date = parse_dt(data['start_date'])

        if 'score' in data:
            video.rating = data['score']

        video.set_empty_fields(NotAvailable)

        return video
